#include <errno.h>
#include <linux/mdio.h>
#include <linux/mii.h>
#include <linux/sockios.h>
#include <net/if.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>
/* Observed PHY1..4 => front LEDs 4,3,2,1, 2026-10-27. */
static const unsigned led_phy[4]={4,3,2,1};
static volatile sig_atomic_t running=1;
static int fd;
static void stop(int sig){(void)sig;running=0;}
static unsigned mode(int link,int activity){return !link?0x8000:activity?0xe000:0xa000;}
static int reg_io(unsigned phy,unsigned reg,int c45,int write,unsigned value){
 struct ifreq req={0};struct mii_ioctl_data *mii=(void *)&req.ifr_data;
 strcpy(req.ifr_name,"wan");mii->phy_id=c45?MDIO_PHY_ID_C45|(phy<<5)|7:phy;
 mii->reg_num=reg;mii->val_in=value;
 if(ioctl(fd,write?SIOCSMIIREG:SIOCGMIIREG,&req)<0)return -1;
 return write?0:mii->val_out;
}
static unsigned long long read_value(unsigned port,const char *name){
 char path[128];unsigned long long value=0;
 snprintf(path,sizeof(path),"/sys/class/net/lan%u/%s",port,name);
 FILE *file=fopen(path,"r");if(file){if(fscanf(file,"%llu",&value)!=1)value=0;fclose(file);}return value;
}
static int monitor(int values[5][4]){
 unsigned long long previous[4]={UINT64_MAX,UINT64_MAX,UINT64_MAX,UINT64_MAX};int result=0;
 signal(SIGTERM,stop);signal(SIGINT,stop);signal(SIGHUP,stop);
 while(running){
  FILE *state=fopen("/var/run/ti04-lan-led.status","w");
  for(unsigned port=1;port<=4;port++){
   unsigned phy=led_phy[port-1];int link=read_value(port,"carrier")==1;
   unsigned long long bytes=read_value(port,"statistics/rx_bytes")+read_value(port,"statistics/tx_bytes");
   int activity=link&&previous[port-1]!=UINT64_MAX&&previous[port-1]!=bytes;
   unsigned desired=(values[phy][3]&0x1fff)|mode(link,activity);int current=reg_io(phy,0x8077,1,0,0);
   if(current<0||(current!=(int)desired&&(reg_io(phy,0x8077,1,1,desired)<0||reg_io(phy,0x8077,1,0,0)!=(int)desired))){
    perror("LAN LED control");running=0;result=6;break;
   }
   if(state)fprintf(state,"lan%u phy_led=%u link=%d activity=%d bytes=%llu control=%04x\n",port,phy,link,activity,bytes,desired);
   previous[port-1]=bytes;
  }
  if(state)fclose(state);
  struct timespec delay={1,0};
  while(running&&nanosleep(&delay,&delay)<0&&errno==EINTR){}
 }
 for(unsigned port=0;port<4;port++)reg_io(led_phy[port],0x8077,1,1,values[led_phy[port]][3]);
 unlink("/var/run/ti04-lan-led.status");return result;
}
int main(int argc,char **argv){
 int values[5][4];int run=argc==2&&!strcmp(argv[1],"--monitor-lan");int restore=argc==2&&!strcmp(argv[1],"--restore-led0");
 if(argc==2&&!strcmp(argv[1],"--self-test")){
  if(mode(0,0)!=0x8000||mode(1,0)!=0xa000||mode(1,1)!=0xe000||led_phy[3]!=1)return 8;
  for(unsigned i=0;i<4;i++)if(led_phy[i]!=4-i)return 8;
  puts("LAN_LED_MAPPING_AND_MODES_SELFTEST=PASS");return 0;
 }
 if(argc>1&&!run&&!restore){fputs("usage: ti04-phy-led [--monitor-lan|--self-test|--restore-led0]\n",stderr);return 9;}
 fd=socket(AF_INET,SOCK_DGRAM,0);if(fd<0){perror("socket");return 1;}
 for(unsigned phy=0;phy<5;phy++){
  int hi=reg_io(phy,MII_PHYSID1,0,0,0),lo=reg_io(phy,MII_PHYSID2,0,0,0);
  if(hi!=0x004d||lo!=0xd0b1){fputs("Expected five QCA8075 PHYs\n",stderr);return 3;}
  printf("phy%u id=%04x%04x",phy,hi,lo);
  for(unsigned reg=0x8074;reg<=0x8077;reg++){
   int value=reg_io(phy,reg,1,0,0);if(value<0){perror("MMD7 LED read");return 4;}
   values[phy][reg-0x8074]=value;printf(" %04x=%04x",reg,value);
  }puts("");
 }
 if(restore)for(unsigned phy=0;phy<5;phy++)if(values[phy][0]==0x0670)
  if(reg_io(phy,0x8074,1,1,0x0630)<0||reg_io(phy,0x8074,1,0,0)!=0x0630)return 6;
 int result=run?monitor(values):0;close(fd);return result;
}
