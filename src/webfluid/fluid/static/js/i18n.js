import { createWS } from "./base.js";

const { request } = createWS("/ws/i18n");

export async function _(string){
    return await request("gettext", { string });
}

export async function _n(string, plural, num){
    return await request("ngettext", { string, plural, num });
}

window.wf.ext.i18n = { _, _n };
