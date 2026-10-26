// Run with Node.js. Exercises the actual LuCI view without a router or browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const code = fs.readFileSync(path.join(root, 'luci/root/www/luci-static/resources/view/network/ti04-power.js'), 'utf8');
const menu = JSON.parse(fs.readFileSync(path.join(root, 'luci/root/usr/share/luci/menu.d/luci-app-ti04-power.json'), 'utf8'));
assert.equal(menu['admin/network/ti04-power'].action.path, 'network/ti04-power');
assert.deepEqual(menu['admin/network/ti04-power'].depends.acl, ['luci-mod-network-config']);

async function check(lang, current, levels) {
	const radios = [{ '.name': 'radio0', type: 'mac80211', band: '2g', country: 'KR', disabled: '1' },
		{ '.name': 'radio1', type: 'mac80211', band: '5g', country: 'KR', disabled: '1' }];
	const writes = [];
	class Value {
		constructor(option) { this.option = option; this.choices = []; }
		value(key, label) { this.choices.push([key, label]); }
		load() { return Promise.resolve(); }
		write(id, value) { writes.push([id, this.option, value]); }
		remove(id) { writes.push([id, this.option, undefined]); }
		static extend(methods) { class Child extends this {} Object.assign(Child.prototype, methods); return Child; }
	}
	class Map {
		constructor(config) { this.config = config; this.sections = []; }
		section(kind, id) {
			const section = { id, options: [], option(Type, name) { const o = new Type(name); this.options.push(o); return o; } };
			this.sections.push(section); return section;
		}
		render() { return this; }
	}
	const uci = { load: async () => {}, sections: () => radios, get: (config, id, option) => current };
	const form = { Map, NamedSection: class {}, DummyValue: Value, ListValue: Value };
	const rpc = { declare(spec) { assert.equal(spec.object, 'iwinfo'); assert.equal(spec.method, 'txpowerlist'); return async () => levels; } };
	const view = new Function('view', 'form', 'rpc', 'uci', 'document', '_', code)(
		{ extend: o => o }, form, rpc, uci, { documentElement: { lang } }, s => s);
	await view.load();
	const map = view.render();
	assert.equal(map.config, 'wireless');
	assert.equal(map.sections.length, 2);
	for (const section of map.sections) {
		assert.equal(section.addremove, false);
		const field = section.options.find(o => o.option === 'txpower');
		assert.deepEqual(section.options.map(o => o.option), ['_enabled', '_country', 'txpower']);
		assert.equal(field.rmempty, true); // Native LuCI removes empty txpower instead of storing a magic maximum.
		await field.load(section.id);
		assert.equal(field.validate(section.id, ''), true);
		assert.notEqual(field.validate(section.id, '35'), true);
		assert(!field.choices.some(([key]) => key === '-5' || key === 'NaN'));
		field.write(section.id, '10');
		field.remove(section.id);
		assert.deepEqual(writes.slice(-2), [[section.id, 'txpower', '10'], [section.id, 'txpower', undefined]]);
		assert.match(field.choices[0][1], lang.startsWith('ko') ? /최대 출력/ : /Maximum allowed/);
		if (current != null) assert.equal(field.validate(section.id, String(current)), true);
	}
	assert(radios.every(r => r.disabled === '1' && r.country === 'KR'));
}

(async () => {
	await check('ko', undefined, [{ dbm: 10 }, { dbm: 23 }, { dbm: -5 }, { dbm: NaN }]);
	await check('en', '17', [{ dbm: 10 }, { dbm: 23 }]); // Preserve an existing limit absent from the latest list.
	await check('ko-KR', '10', []); // Radios may be off and have no enumerated manual levels.
	console.log('PASS: auto/manual mapping, radio isolation, offered limits, existing values, Korean/English and menu ACL');
})().catch(error => { console.error(error); process.exitCode = 1; });
