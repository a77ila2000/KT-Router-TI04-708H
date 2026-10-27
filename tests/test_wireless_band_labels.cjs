const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../luci/patches/render_radio_badge.js'), 'utf8');
const E = (tag, attrs, children) => ({ tag, attrs: attrs || {}, children });
const L = { resource: value => ({ format: suffix => value.replace('%s', suffix) }) };
const render = new Function('E', 'L', `${source}; return render_radio_badge;`)(E, L);
const text = node => node == null ? '' : typeof node === 'string' ? node :
    Array.isArray(node) ? node.map(text).join('') : text(node.children);
function check(id, band, up, expected, runtimeBand) {
    const device = Object.freeze({ getName: () => id, get: option => {
        assert.equal(option, 'band'); return band;
    }, ubus: (...parts) => {
        assert.deepEqual(parts, ['dev', 'config', 'band']); return runtimeBand;
    }, isUp: () => up });
    const badge = render(device);
    assert.equal(badge.attrs.title, id);
    assert.equal(text(badge).trim(), expected ? expected + id : id);
    assert.equal(badge.children[0].attrs.src, up ? 'icons/wifi.svg' : 'icons/wifi_disabled.svg');
    if (expected) assert.equal(badge.children[2].children[0].tag, 'strong');
}
check('radio0', '2g', false, '2.4GHz Wi-Fi');
check('radio1', '5g', true, '5GHz Wi-Fi');
check('radio0', '5g', false, '5GHz Wi-Fi'); // Band comes from configuration, never the radio number.
check('radio9', '6g', true, '6GHz Wi-Fi');
check('radio7', undefined, false, null);
check('radio7', 'constructor', true, null);
check('radio9', undefined, false, '5GHz Wi-Fi', '5g');
console.log('PASS: configured band labels, disabled radios, swapped IDs and unknown-band fallback');
