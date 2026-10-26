'use strict';
'require view';
'require form';
'require rpc';
'require uci';

const text = (en, ko) => /^ko\b/i.test(document.documentElement.lang) ? ko : en;
const powerList = rpc.declare({
	object: 'iwinfo', method: 'txpowerlist', params: ['device'], expect: { results: [] }
});

const PowerValue = form.ListValue.extend({
	load: function(section_id) {
		return powerList(section_id).then(list => {
			this.allowed = new Set(['']);
			this.value('', text('Maximum allowed (automatic)', '최대 출력(자동)'));
			for (const level of list) {
				if (!Number.isInteger(level.dbm) || level.dbm < 0)
					continue;
				const value = String(level.dbm);
				if (!this.allowed.has(value)) {
					this.allowed.add(value);
					this.value(value, text('Manual limit: ', '수동 상한: ') + value + ' dBm');
				}
			}
			const current = uci.get('wireless', section_id, 'txpower');
			if (current != null && !this.allowed.has(String(current))) {
				this.allowed.add(String(current));
				this.value(String(current), text('Current setting: ', '현재 설정: ') + current + ' dBm');
			}
			return form.ListValue.prototype.load.call(this, section_id);
		});
	},
	validate: function(section_id, value) {
		return this.allowed.has(value == null ? '' : String(value)) ||
			text('Choose automatic or a listed power limit.', '자동 또는 목록의 출력 상한을 선택하세요.');
	}
});

return view.extend({
	load: function() {
		return uci.load('wireless');
	},
	render: function() {
		const m = new form.Map('wireless', _('Maximum transmit power'), text(
			'Automatic uses the maximum permitted by the driver for the current country, channel and device. Actual power may be lower. Saving does not enable a disabled radio.',
			'자동은 현재 국가·채널·장치 조건에서 드라이버가 허용하는 최대 출력을 사용합니다. 실제 출력은 낮아질 수 있습니다. 꺼진 무선은 이 설정을 저장해도 켜지지 않습니다.'));

		for (const radio of uci.sections('wireless', 'wifi-device')) {
			if (radio.type !== 'mac80211')
				continue;
			const band = { '2g': '2.4 GHz', '5g': '5 GHz', '6g': '6 GHz' }[radio.band] || radio['.name'];
			const s = m.section(form.NamedSection, radio['.name'], 'wifi-device', band);
			s.addremove = false;

			let o = s.option(form.DummyValue, '_enabled', _('Wireless'));
			o.cfgvalue = () => radio.disabled === '1' ? text('Disabled', '비활성화') : text('Enabled in configuration', '사용하도록 설정됨');
			o = s.option(form.DummyValue, '_country', _('Country Code'));
			o.cfgvalue = () => radio.country || text('Driver default', '드라이버 기본값');

			o = s.option(PowerValue, 'txpower', text('Output profile', '출력 프로필'));
			o.rmempty = true;
			o.default = '';
			o.description = text(
				'Automatic removes the manual limit. Manual values use the same setting as Network → Wireless.',
				'자동은 수동 출력 상한을 해제합니다. 수동값은 네트워크 → 무선의 송신 출력 설정과 연동됩니다.');
		}
		return m.render();
	}
});
