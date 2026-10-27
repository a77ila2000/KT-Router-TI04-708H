function render_radio_badge(radioDev) {
	const id = radioDev.getName();
	const band = radioDev.get('band');
	const label = band === '2g' ? '2.4GHz Wi-Fi' :
		band === '5g' ? '5GHz Wi-Fi' :
		band === '6g' ? '6GHz Wi-Fi' : null;
	return E('span', { 'class': 'ifacebadge', 'title': id }, [
		E('img', { 'src': L.resource('icons/wifi%s.svg').format(radioDev.isUp() ? '' : '_disabled') }),
		' ',
		label ? E('span', {}, [E('strong', {}, label), E('br'), E('small', {}, id)]) : id
	]);
}
