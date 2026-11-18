#!/usr/bin/env node
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __require = /* @__PURE__ */ ((x) => typeof require !== "undefined" ? require : typeof Proxy !== "undefined" ? new Proxy(x, {
  get: (a, b) => (typeof require !== "undefined" ? require : a)[b]
}) : x)(function(x) {
  if (typeof require !== "undefined") return require.apply(this, arguments);
  throw Error('Dynamic require of "' + x + '" is not supported');
});
var __esm = (fn, res) => function __init() {
  return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
};
var __commonJS = (cb, mod) => function __require2() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// node_modules/emoji-regex/index.js
var require_emoji_regex = __commonJS({
  "node_modules/emoji-regex/index.js"(exports, module) {
    module.exports = () => {
      return /[#*0-9]\uFE0F?\u20E3|[\xA9\xAE\u203C\u2049\u2122\u2139\u2194-\u2199\u21A9\u21AA\u231A\u231B\u2328\u23CF\u23ED-\u23EF\u23F1\u23F2\u23F8-\u23FA\u24C2\u25AA\u25AB\u25B6\u25C0\u25FB\u25FC\u25FE\u2600-\u2604\u260E\u2611\u2614\u2615\u2618\u2620\u2622\u2623\u2626\u262A\u262E\u262F\u2638-\u263A\u2640\u2642\u2648-\u2653\u265F\u2660\u2663\u2665\u2666\u2668\u267B\u267E\u267F\u2692\u2694-\u2697\u2699\u269B\u269C\u26A0\u26A7\u26AA\u26B0\u26B1\u26BD\u26BE\u26C4\u26C8\u26CF\u26D1\u26E9\u26F0-\u26F5\u26F7\u26F8\u26FA\u2702\u2708\u2709\u270F\u2712\u2714\u2716\u271D\u2721\u2733\u2734\u2744\u2747\u2757\u2763\u27A1\u2934\u2935\u2B05-\u2B07\u2B1B\u2B1C\u2B55\u3030\u303D\u3297\u3299]\uFE0F?|[\u261D\u270C\u270D](?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?|[\u270A\u270B](?:\uD83C[\uDFFB-\uDFFF])?|[\u23E9-\u23EC\u23F0\u23F3\u25FD\u2693\u26A1\u26AB\u26C5\u26CE\u26D4\u26EA\u26FD\u2705\u2728\u274C\u274E\u2753-\u2755\u2795-\u2797\u27B0\u27BF\u2B50]|\u26D3\uFE0F?(?:\u200D\uD83D\uDCA5)?|\u26F9(?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?(?:\u200D[\u2640\u2642]\uFE0F?)?|\u2764\uFE0F?(?:\u200D(?:\uD83D\uDD25|\uD83E\uDE79))?|\uD83C(?:[\uDC04\uDD70\uDD71\uDD7E\uDD7F\uDE02\uDE37\uDF21\uDF24-\uDF2C\uDF36\uDF7D\uDF96\uDF97\uDF99-\uDF9B\uDF9E\uDF9F\uDFCD\uDFCE\uDFD4-\uDFDF\uDFF5\uDFF7]\uFE0F?|[\uDF85\uDFC2\uDFC7](?:\uD83C[\uDFFB-\uDFFF])?|[\uDFC4\uDFCA](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDFCB\uDFCC](?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDCCF\uDD8E\uDD91-\uDD9A\uDE01\uDE1A\uDE2F\uDE32-\uDE36\uDE38-\uDE3A\uDE50\uDE51\uDF00-\uDF20\uDF2D-\uDF35\uDF37-\uDF43\uDF45-\uDF4A\uDF4C-\uDF7C\uDF7E-\uDF84\uDF86-\uDF93\uDFA0-\uDFC1\uDFC5\uDFC6\uDFC8\uDFC9\uDFCF-\uDFD3\uDFE0-\uDFF0\uDFF8-\uDFFF]|\uDDE6\uD83C[\uDDE8-\uDDEC\uDDEE\uDDF1\uDDF2\uDDF4\uDDF6-\uDDFA\uDDFC\uDDFD\uDDFF]|\uDDE7\uD83C[\uDDE6\uDDE7\uDDE9-\uDDEF\uDDF1-\uDDF4\uDDF6-\uDDF9\uDDFB\uDDFC\uDDFE\uDDFF]|\uDDE8\uD83C[\uDDE6\uDDE8\uDDE9\uDDEB-\uDDEE\uDDF0-\uDDF7\uDDFA-\uDDFF]|\uDDE9\uD83C[\uDDEA\uDDEC\uDDEF\uDDF0\uDDF2\uDDF4\uDDFF]|\uDDEA\uD83C[\uDDE6\uDDE8\uDDEA\uDDEC\uDDED\uDDF7-\uDDFA]|\uDDEB\uD83C[\uDDEE-\uDDF0\uDDF2\uDDF4\uDDF7]|\uDDEC\uD83C[\uDDE6\uDDE7\uDDE9-\uDDEE\uDDF1-\uDDF3\uDDF5-\uDDFA\uDDFC\uDDFE]|\uDDED\uD83C[\uDDF0\uDDF2\uDDF3\uDDF7\uDDF9\uDDFA]|\uDDEE\uD83C[\uDDE8-\uDDEA\uDDF1-\uDDF4\uDDF6-\uDDF9]|\uDDEF\uD83C[\uDDEA\uDDF2\uDDF4\uDDF5]|\uDDF0\uD83C[\uDDEA\uDDEC-\uDDEE\uDDF2\uDDF3\uDDF5\uDDF7\uDDFC\uDDFE\uDDFF]|\uDDF1\uD83C[\uDDE6-\uDDE8\uDDEE\uDDF0\uDDF7-\uDDFB\uDDFE]|\uDDF2\uD83C[\uDDE6\uDDE8-\uDDED\uDDF0-\uDDFF]|\uDDF3\uD83C[\uDDE6\uDDE8\uDDEA-\uDDEC\uDDEE\uDDF1\uDDF4\uDDF5\uDDF7\uDDFA\uDDFF]|\uDDF4\uD83C\uDDF2|\uDDF5\uD83C[\uDDE6\uDDEA-\uDDED\uDDF0-\uDDF3\uDDF7-\uDDF9\uDDFC\uDDFE]|\uDDF6\uD83C\uDDE6|\uDDF7\uD83C[\uDDEA\uDDF4\uDDF8\uDDFA\uDDFC]|\uDDF8\uD83C[\uDDE6-\uDDEA\uDDEC-\uDDF4\uDDF7-\uDDF9\uDDFB\uDDFD-\uDDFF]|\uDDF9\uD83C[\uDDE6\uDDE8\uDDE9\uDDEB-\uDDED\uDDEF-\uDDF4\uDDF7\uDDF9\uDDFB\uDDFC\uDDFF]|\uDDFA\uD83C[\uDDE6\uDDEC\uDDF2\uDDF3\uDDF8\uDDFE\uDDFF]|\uDDFB\uD83C[\uDDE6\uDDE8\uDDEA\uDDEC\uDDEE\uDDF3\uDDFA]|\uDDFC\uD83C[\uDDEB\uDDF8]|\uDDFD\uD83C\uDDF0|\uDDFE\uD83C[\uDDEA\uDDF9]|\uDDFF\uD83C[\uDDE6\uDDF2\uDDFC]|\uDF44(?:\u200D\uD83D\uDFEB)?|\uDF4B(?:\u200D\uD83D\uDFE9)?|\uDFC3(?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D(?:[\u2640\u2642]\uFE0F?(?:\u200D\u27A1\uFE0F?)?|\u27A1\uFE0F?))?|\uDFF3\uFE0F?(?:\u200D(?:\u26A7\uFE0F?|\uD83C\uDF08))?|\uDFF4(?:\u200D\u2620\uFE0F?|\uDB40\uDC67\uDB40\uDC62\uDB40(?:\uDC65\uDB40\uDC6E\uDB40\uDC67|\uDC73\uDB40\uDC63\uDB40\uDC74|\uDC77\uDB40\uDC6C\uDB40\uDC73)\uDB40\uDC7F)?)|\uD83D(?:[\uDC3F\uDCFD\uDD49\uDD4A\uDD6F\uDD70\uDD73\uDD76-\uDD79\uDD87\uDD8A-\uDD8D\uDDA5\uDDA8\uDDB1\uDDB2\uDDBC\uDDC2-\uDDC4\uDDD1-\uDDD3\uDDDC-\uDDDE\uDDE1\uDDE3\uDDE8\uDDEF\uDDF3\uDDFA\uDECB\uDECD-\uDECF\uDEE0-\uDEE5\uDEE9\uDEF0\uDEF3]\uFE0F?|[\uDC42\uDC43\uDC46-\uDC50\uDC66\uDC67\uDC6B-\uDC6D\uDC72\uDC74-\uDC76\uDC78\uDC7C\uDC83\uDC85\uDC8F\uDC91\uDCAA\uDD7A\uDD95\uDD96\uDE4C\uDE4F\uDEC0\uDECC](?:\uD83C[\uDFFB-\uDFFF])?|[\uDC6E-\uDC71\uDC73\uDC77\uDC81\uDC82\uDC86\uDC87\uDE45-\uDE47\uDE4B\uDE4D\uDE4E\uDEA3\uDEB4\uDEB5](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDD74\uDD90](?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?|[\uDC00-\uDC07\uDC09-\uDC14\uDC16-\uDC25\uDC27-\uDC3A\uDC3C-\uDC3E\uDC40\uDC44\uDC45\uDC51-\uDC65\uDC6A\uDC79-\uDC7B\uDC7D-\uDC80\uDC84\uDC88-\uDC8E\uDC90\uDC92-\uDCA9\uDCAB-\uDCFC\uDCFF-\uDD3D\uDD4B-\uDD4E\uDD50-\uDD67\uDDA4\uDDFB-\uDE2D\uDE2F-\uDE34\uDE37-\uDE41\uDE43\uDE44\uDE48-\uDE4A\uDE80-\uDEA2\uDEA4-\uDEB3\uDEB7-\uDEBF\uDEC1-\uDEC5\uDED0-\uDED2\uDED5-\uDED8\uDEDC-\uDEDF\uDEEB\uDEEC\uDEF4-\uDEFC\uDFE0-\uDFEB\uDFF0]|\uDC08(?:\u200D\u2B1B)?|\uDC15(?:\u200D\uD83E\uDDBA)?|\uDC26(?:\u200D(?:\u2B1B|\uD83D\uDD25))?|\uDC3B(?:\u200D\u2744\uFE0F?)?|\uDC41\uFE0F?(?:\u200D\uD83D\uDDE8\uFE0F?)?|\uDC68(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDC68\uDC69]\u200D\uD83D(?:\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?)|[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?)|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]))|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC68\uD83C[\uDFFC-\uDFFF])|\uD83E(?:[\uDD1D\uDEEF]\u200D\uD83D\uDC68\uD83C[\uDFFC-\uDFFF]|[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC68\uD83C[\uDFFB\uDFFD-\uDFFF])|\uD83E(?:[\uDD1D\uDEEF]\u200D\uD83D\uDC68\uD83C[\uDFFB\uDFFD-\uDFFF]|[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC68\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])|\uD83E(?:[\uDD1D\uDEEF]\u200D\uD83D\uDC68\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF]|[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC68\uD83C[\uDFFB-\uDFFD\uDFFF])|\uD83E(?:[\uDD1D\uDEEF]\u200D\uD83D\uDC68\uD83C[\uDFFB-\uDFFD\uDFFF]|[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?\uDC68\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC68\uD83C[\uDFFB-\uDFFE])|\uD83E(?:[\uDD1D\uDEEF]\u200D\uD83D\uDC68\uD83C[\uDFFB-\uDFFE]|[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3])))?))?|\uDC69(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:\uDC8B\u200D\uD83D)?[\uDC68\uDC69]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?|\uDC69\u200D\uD83D(?:\uDC66(?:\u200D\uD83D\uDC66)?|\uDC67(?:\u200D\uD83D[\uDC66\uDC67])?))|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]))|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC69\uD83C[\uDFFC-\uDFFF])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFC-\uDFFF]|\uDEEF\u200D\uD83D\uDC69\uD83C[\uDFFC-\uDFFF])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC69\uD83C[\uDFFB\uDFFD-\uDFFF])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB\uDFFD-\uDFFF]|\uDEEF\u200D\uD83D\uDC69\uD83C[\uDFFB\uDFFD-\uDFFF])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC69\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF]|\uDEEF\u200D\uD83D\uDC69\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC69\uD83C[\uDFFB-\uDFFD\uDFFF])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB-\uDFFD\uDFFF]|\uDEEF\u200D\uD83D\uDC69\uD83C[\uDFFB-\uDFFD\uDFFF])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D\uD83D(?:[\uDC68\uDC69]|\uDC8B\u200D\uD83D[\uDC68\uDC69])\uD83C[\uDFFB-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83D\uDC69\uD83C[\uDFFB-\uDFFE])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3]|\uDD1D\u200D\uD83D[\uDC68\uDC69]\uD83C[\uDFFB-\uDFFE]|\uDEEF\u200D\uD83D\uDC69\uD83C[\uDFFB-\uDFFE])))?))?|\uDD75(?:\uD83C[\uDFFB-\uDFFF]|\uFE0F)?(?:\u200D[\u2640\u2642]\uFE0F?)?|\uDE2E(?:\u200D\uD83D\uDCA8)?|\uDE35(?:\u200D\uD83D\uDCAB)?|\uDE36(?:\u200D\uD83C\uDF2B\uFE0F?)?|\uDE42(?:\u200D[\u2194\u2195]\uFE0F?)?|\uDEB6(?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D(?:[\u2640\u2642]\uFE0F?(?:\u200D\u27A1\uFE0F?)?|\u27A1\uFE0F?))?)|\uD83E(?:[\uDD0C\uDD0F\uDD18-\uDD1F\uDD30-\uDD34\uDD36\uDD77\uDDB5\uDDB6\uDDBB\uDDD2\uDDD3\uDDD5\uDEC3-\uDEC5\uDEF0\uDEF2-\uDEF8](?:\uD83C[\uDFFB-\uDFFF])?|[\uDD26\uDD35\uDD37-\uDD39\uDD3C-\uDD3E\uDDB8\uDDB9\uDDCD\uDDCF\uDDD4\uDDD6-\uDDDD](?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDDDE\uDDDF](?:\u200D[\u2640\u2642]\uFE0F?)?|[\uDD0D\uDD0E\uDD10-\uDD17\uDD20-\uDD25\uDD27-\uDD2F\uDD3A\uDD3F-\uDD45\uDD47-\uDD76\uDD78-\uDDB4\uDDB7\uDDBA\uDDBC-\uDDCC\uDDD0\uDDE0-\uDDFF\uDE70-\uDE7C\uDE80-\uDE8A\uDE8E-\uDEC2\uDEC6\uDEC8\uDECD-\uDEDC\uDEDF-\uDEEA\uDEEF]|\uDDCE(?:\uD83C[\uDFFB-\uDFFF])?(?:\u200D(?:[\u2640\u2642]\uFE0F?(?:\u200D\u27A1\uFE0F?)?|\u27A1\uFE0F?))?|\uDDD1(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3\uDE70]|\uDD1D\u200D\uD83E\uDDD1|\uDDD1\u200D\uD83E\uDDD2(?:\u200D\uD83E\uDDD2)?|\uDDD2(?:\u200D\uD83E\uDDD2)?))|\uD83C(?:\uDFFB(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFC-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83E\uDDD1\uD83C[\uDFFC-\uDFFF])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3\uDE70]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF]|\uDEEF\u200D\uD83E\uDDD1\uD83C[\uDFFC-\uDFFF])))?|\uDFFC(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB\uDFFD-\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83E\uDDD1\uD83C[\uDFFB\uDFFD-\uDFFF])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3\uDE70]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF]|\uDEEF\u200D\uD83E\uDDD1\uD83C[\uDFFB\uDFFD-\uDFFF])))?|\uDFFD(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83E\uDDD1\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3\uDE70]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF]|\uDEEF\u200D\uD83E\uDDD1\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])))?|\uDFFE(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB-\uDFFD\uDFFF]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFD\uDFFF])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3\uDE70]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF]|\uDEEF\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFD\uDFFF])))?|\uDFFF(?:\u200D(?:[\u2695\u2696\u2708]\uFE0F?|\u2764\uFE0F?\u200D(?:\uD83D\uDC8B\u200D)?\uD83E\uDDD1\uD83C[\uDFFB-\uDFFE]|\uD83C[\uDF3E\uDF73\uDF7C\uDF84\uDF93\uDFA4\uDFA8\uDFEB\uDFED]|\uD83D(?:[\uDCBB\uDCBC\uDD27\uDD2C\uDE80\uDE92]|\uDC30\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFE])|\uD83E(?:[\uDDAF\uDDBC\uDDBD](?:\u200D\u27A1\uFE0F?)?|[\uDDB0-\uDDB3\uDE70]|\uDD1D\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFF]|\uDEEF\u200D\uD83E\uDDD1\uD83C[\uDFFB-\uDFFE])))?))?|\uDEF1(?:\uD83C(?:\uDFFB(?:\u200D\uD83E\uDEF2\uD83C[\uDFFC-\uDFFF])?|\uDFFC(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB\uDFFD-\uDFFF])?|\uDFFD(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB\uDFFC\uDFFE\uDFFF])?|\uDFFE(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB-\uDFFD\uDFFF])?|\uDFFF(?:\u200D\uD83E\uDEF2\uD83C[\uDFFB-\uDFFE])?))?)/g;
    };
  }
});

// node_modules/smol-toml/dist/error.js
function getLineColFromPtr(string, ptr) {
  let lines = string.slice(0, ptr).split(/\r?\n/);
  return [lines.length, lines.pop().length + 1];
}
function makeCodeBlock(string, line, column) {
  let lines = string.split(/\r?\n/);
  let codeblock = "";
  let numberLen = (Math.log10(line + 1) | 0) + 1;
  for (let i = line - 1; i <= line + 1; i++) {
    let l = lines[i - 1];
    if (!l)
      continue;
    codeblock += i.toString().padEnd(numberLen, " ");
    codeblock += ":  ";
    codeblock += l;
    codeblock += "\n";
    if (i === line) {
      codeblock += " ".repeat(numberLen + column + 2);
      codeblock += "^\n";
    }
  }
  return codeblock;
}
var TomlError;
var init_error = __esm({
  "node_modules/smol-toml/dist/error.js"() {
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
    TomlError = class _TomlError extends Error {
      line;
      column;
      codeblock;
      constructor(message, options2) {
        const [line, column] = getLineColFromPtr(options2.toml, options2.ptr);
        const codeblock = makeCodeBlock(options2.toml, line, column);
        super(`Invalid TOML document: ${message}

${codeblock}`, options2);
        this.line = line;
        this.column = column;
        this.codeblock = codeblock;
      }
      /** @internal */
      static x(message, ctx, ptr) {
        throw new _TomlError(message, { toml: ctx.s, ptr: ptr ?? ctx.p });
      }
    };
  }
});

// node_modules/smol-toml/dist/primitive.js
function parseString(ctx) {
  let startPtr = ctx.p;
  let c = ctx.s.charCodeAt(ctx.p++);
  let first = c;
  let isLiteral = c === 39;
  let isMultiline = c === ctx.s.charCodeAt(ctx.p) && c === ctx.s.charCodeAt(ctx.p + 1);
  if (isMultiline) {
    if ((c = ctx.s.charCodeAt(ctx.p += 2)) === 10)
      ctx.p++;
    else if (c === 13 && ctx.s.charCodeAt(ctx.p + 1) === 10)
      ctx.p += 2;
  }
  let parsed = "";
  let sliceStart = ctx.p;
  let state = 0;
  for (; ctx.p < ctx.s.length; ctx.p++) {
    c = ctx.s.charCodeAt(ctx.p);
    if (isMultiline && (c === 10 || c === 13 && ctx.s.charCodeAt(ctx.p + 1) === 10)) {
      state = state && 3;
    } else if (c < 32 && c !== 9 || c === 127) {
      TomlError.x("control characters are not allowed in strings", ctx);
    } else if ((!state || state === 3) && c === first && (!isMultiline || ctx.s.charCodeAt(ctx.p + 1) === first && ctx.s.charCodeAt(ctx.p + 2) === first)) {
      if (isMultiline) {
        if (ctx.s.charCodeAt(ctx.p + 3) === first)
          ctx.p++;
        if (ctx.s.charCodeAt(ctx.p + 3) === first)
          ctx.p++;
      }
      if (!state) {
        let s = ctx.s.slice(sliceStart, ctx.p);
        parsed = parsed ? parsed + s : s;
      }
      ctx.p += isMultiline ? 3 : 1;
      return parsed;
    } else if (!state) {
      if (!isLiteral && c === 92) {
        parsed += ctx.s.slice(sliceStart, sliceStart = ctx.p);
        state = 1;
      }
    } else if (state === 1) {
      if (c === 120 || c === 117 || c === 85) {
        let errPtr = ctx.p++ - 1;
        let value = 0;
        let len = c === 120 ? 2 : c === 117 ? 4 : 8;
        for (let j = 0; j < len; j++, ctx.p++) {
          let hex = ctx.s.charCodeAt(ctx.p);
          let digit = (
            /* 0-9 */
            hex >= 48 && hex <= 57 ? hex - 48 : (
              /* A-F */
              hex >= 65 && hex <= 70 ? hex - 65 + 10 : (
                /* a-f */
                hex >= 97 && hex <= 102 ? hex - 97 + 10 : -1
              )
            )
          );
          if (digit < 0)
            TomlError.x("invalid non-hex character in unicode escape", ctx);
          value = value << 4 | digit;
        }
        if (value < 0 || value > 1114111 || value >= 55296 && value <= 57343) {
          TomlError.x("invalid unicode escape", ctx, errPtr);
        }
        parsed += String.fromCodePoint(value);
        sliceStart = ctx.p--;
        state = 0;
      } else if (isMultiline && (c === 32 || c === 9)) {
        state = 2;
      } else {
        if (c === 98)
          parsed += "\b";
        else if (c === 116)
          parsed += "	";
        else if (c === 110)
          parsed += "\n";
        else if (c === 102)
          parsed += "\f";
        else if (c === 114)
          parsed += "\r";
        else if (c === 101)
          parsed += "\x1B";
        else if (c === 34)
          parsed += '"';
        else if (c === 92)
          parsed += "\\";
        else
          TomlError.x("unrecognised escape sequence", ctx);
        sliceStart = ctx.p + 1;
        state = 0;
      }
    } else if (c !== 32 && c !== 9) {
      if (state === 2)
        TomlError.x("invalid escape: only line-ending whitespace may be escaped", ctx, sliceStart);
      state = !isLiteral && c === 92 ? 1 : 0;
      sliceStart = ctx.p;
    }
  }
  TomlError.x("unfinished string", ctx, startPtr);
}
var init_primitive = __esm({
  "node_modules/smol-toml/dist/primitive.js"() {
    init_error();
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
  }
});

// node_modules/smol-toml/dist/date.js
var DATE_TIME_RE, TomlDate;
var init_date = __esm({
  "node_modules/smol-toml/dist/date.js"() {
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
    DATE_TIME_RE = /^(\d{4}-\d{2}-\d{2})?[Tt ]?(?:(\d{2}):\d{2}(?::\d{2}(?:\.\d+)?)?)?(Z|z|[-+]\d{2}:\d{2})?$/i;
    TomlDate = class _TomlDate extends Date {
      #hasDate = false;
      #hasTime = false;
      #offset = null;
      constructor(date, fasttype, unsafeDelim) {
        let hasDate = true;
        let hasTime = true;
        let offset = "Z";
        let c;
        if (typeof date === "string") {
          if (fasttype)
            prep: {
              if (fasttype < 3) {
                if (+date.slice(11, 13) > 23) {
                  date = "";
                  break prep;
                }
                if (fasttype === 2) {
                  offset = null;
                  date += "Z";
                } else if ((c = date.charCodeAt(date.length - 1)) !== 90 && c !== 122) {
                  offset = date.slice(date.length - 6);
                }
                if (unsafeDelim)
                  date = date.slice(0, 10) + "T" + date.slice(11);
              } else if (fasttype === 4) {
                date = +date.slice(0, 2) > 23 ? "" : `0000-01-01T${date}Z`;
              }
              hasDate = fasttype !== 4;
              hasTime = fasttype !== 3;
            }
          else {
            let match = date.match(DATE_TIME_RE);
            if (match) {
              if (!match[1]) {
                hasDate = false;
                date = `0000-01-01T${date}`;
              }
              hasTime = !!match[2];
              hasTime && date[10] === " " && (date = date.replace(" ", "T"));
              if (match[2] && +match[2] > 23) {
                date = "";
              } else {
                offset = match[3] || null;
                if (!offset && hasTime)
                  date += "Z";
              }
            } else {
              date = "";
            }
          }
        }
        super(date);
        if (!isNaN(this.getTime())) {
          this.#hasDate = hasDate;
          this.#hasTime = hasTime;
          this.#offset = offset;
        }
      }
      isDateTime() {
        return this.#hasDate && this.#hasTime;
      }
      isLocal() {
        return !this.#hasDate || !this.#hasTime || !this.#offset;
      }
      isDate() {
        return this.#hasDate && !this.#hasTime;
      }
      isTime() {
        return this.#hasTime && !this.#hasDate;
      }
      isValid() {
        return this.#hasDate || this.#hasTime;
      }
      toISOString() {
        let iso = super.toISOString();
        if (this.isDate())
          return iso.slice(0, 10);
        if (this.isTime())
          return iso.slice(11, 23);
        if (this.#offset === null)
          return iso.slice(0, -1);
        if (this.#offset === "Z" || this.#offset === "z")
          return iso;
        let offset = +this.#offset.slice(1, 3) * 60 + +this.#offset.slice(4, 6);
        offset = this.#offset[0] === "-" ? offset : -offset;
        let offsetDate = new Date(this.getTime() - offset * 6e4);
        return offsetDate.toISOString().slice(0, -1) + this.#offset;
      }
      static wrapAsOffsetDateTime(jsDate, offset = "Z") {
        let date = new _TomlDate(jsDate);
        date.#offset = offset;
        return date;
      }
      static wrapAsLocalDateTime(jsDate) {
        let date = new _TomlDate(jsDate);
        date.#offset = null;
        return date;
      }
      static wrapAsLocalDate(jsDate) {
        let date = new _TomlDate(jsDate);
        date.#hasTime = false;
        date.#offset = null;
        return date;
      }
      static wrapAsLocalTime(jsDate) {
        let date = new _TomlDate(jsDate);
        date.#hasDate = false;
        date.#offset = null;
        return date;
      }
    };
  }
});

// node_modules/smol-toml/dist/extract.js
function isDigit(char, base = 10) {
  return base === 16 ? char > 47 && char < 58 || char > 64 && char < 71 || char > 96 && char < 103 : char > 47 && char < 48 + base;
}
function isEndOfValue(char, delim) {
  return char === 32 || char === 9 || char === 10 || char === 13 || // Structure end or next value delimiter
  delim && (char === delim || char === 44) || // Comment
  char === 35;
}
function extractValue(ctx, end) {
  let errPtr = ctx.p;
  let c = ctx.s.charCodeAt(ctx.p);
  if (c === 91 || c === 123) {
    ctx.d-- || TomlError.x("document contains excessively nested structures. aborting.", ctx);
    let value = c === 91 ? parseArray(ctx) : parseInlineTable(ctx);
    ctx.d++;
    return value;
  }
  if (c === 34 || c === 39) {
    return parseString(ctx);
  }
  if (c === 116) {
    if (ctx.s.charCodeAt(++ctx.p) !== 114 || ctx.s.charCodeAt(++ctx.p) !== 117 || ctx.s.charCodeAt(++ctx.p) !== 101)
      TomlError.x("invalid value", ctx, errPtr);
    return ctx.p++, true;
  }
  if (c === 102) {
    if (ctx.s.charCodeAt(++ctx.p) !== 97 || ctx.s.charCodeAt(++ctx.p) !== 108 || ctx.s.charCodeAt(++ctx.p) !== 115 || ctx.s.charCodeAt(++ctx.p) !== 101)
      TomlError.x("invalid value", ctx, errPtr);
    return ctx.p++, false;
  }
  if (c === 43 || c === 45) {
    return parseNumber(ctx, ctx.p, ctx.s.charCodeAt(++ctx.p), 44 - c, end);
  }
  if (ctx.s.charCodeAt(ctx.p + 4) === 45 && ctx.s.charCodeAt(ctx.p + 7) === 45) {
    return parseDate(ctx, c, end);
  }
  if (ctx.s.charCodeAt(ctx.p + 2) === 58) {
    return parseTime(ctx, c, end);
  }
  return parseNumber(ctx, ctx.p, c, 0, end);
}
function parseNumber(ctx, startPtr, startChr, sign, endChr) {
  let c = startChr;
  let state = 0;
  let hasUnderscores = false;
  if (c === 105) {
    if (ctx.s.charCodeAt(++ctx.p) !== 110 || ctx.s.charCodeAt(++ctx.p) !== 102)
      TomlError.x("invalid value", ctx, startPtr);
    return ctx.p++, (sign || 1) / 0;
  }
  if (c === 110) {
    if (ctx.s.charCodeAt(++ctx.p) !== 97 || ctx.s.charCodeAt(++ctx.p) !== 110)
      TomlError.x("invalid value", ctx, startPtr);
    return ctx.p++, NaN;
  }
  if (c === 48) {
    if (++ctx.p >= ctx.s.length || isEndOfValue(c = ctx.s.charCodeAt(ctx.p), endChr))
      return ctx.bi === true ? 0n : 0;
    if (!sign) {
      if (c === 120)
        return parseIntegerBaseN(ctx, startPtr, 16, endChr);
      else if (c === 98)
        return parseIntegerBaseN(ctx, startPtr, 2, endChr);
      else if (c === 111)
        return parseIntegerBaseN(ctx, startPtr, 8, endChr);
    }
    if (c === 46)
      state = 2;
    else if (c === 101 || c === 69)
      state = 4;
    else
      TomlError.x("illegal leading zero", ctx, startPtr);
  } else if (!isDigit(c))
    TomlError.x("invalid value", ctx, startPtr);
  while (++ctx.p < ctx.s.length && (c = ctx.s.charCodeAt(ctx.p), !isEndOfValue(c, endChr))) {
    if (!state)
      state = 1;
    if (c === 95) {
      if (!(state & 1))
        TomlError.x("illegal underscore", ctx);
      state += 11;
      hasUnderscores = true;
    } else if (state === 1 && c === 46)
      state = 2;
    else if ((state === 1 || state === 3) && (c === 101 || c === 69))
      state = 4;
    else if (state === 4 && (c === 43 || c === 45)) {
      state = 6;
    } else if (!isDigit(c))
      TomlError.x(`illegal character in numeric literal`, ctx);
    else if (state > 9)
      state -= 11;
    else if (!(state & 1))
      state++;
  }
  if (!state) {
    let val = (startChr - 48) * (sign || 1);
    return ctx.bi === true ? BigInt(val) : val;
  }
  if (!(state & 1))
    TomlError.x("unfinished numeric value", ctx, startPtr);
  let str = ctx.s.slice(startPtr, ctx.p);
  if (hasUnderscores)
    str = str.replaceAll("_", "");
  return state > 1 ? parseFloat(str) : parseInteger(ctx, str, 10, startPtr);
}
function parseIntegerBaseN(ctx, startPtr, base, endChr) {
  let c, underscore = 1;
  while (++ctx.p < ctx.s.length && (c = ctx.s.charCodeAt(ctx.p), !isEndOfValue(c, endChr))) {
    if (c === 95) {
      if (underscore & 1)
        TomlError.x("illegal underscore", ctx);
      underscore = 3;
    } else if (!isDigit(c, base))
      TomlError.x(`illegal character in numeric literal`, ctx);
    else if (underscore & 1)
      underscore--;
  }
  if (underscore & 1)
    TomlError.x("unfinished numeric value", ctx);
  let str = ctx.s.slice(startPtr + 2, ctx.p);
  if (underscore)
    str = str.replaceAll("_", "");
  return parseInteger(ctx, str, base, startPtr);
}
function parseInteger(ctx, str, base, startPtr) {
  if (ctx.bi !== true)
    int: {
      let val = parseInt(str, base);
      if (!Number.isSafeInteger(val)) {
        if (ctx.bi)
          break int;
        TomlError.x("integer value cannot be represented losslessly", ctx, startPtr);
      }
      return val;
    }
  return base === 10 ? BigInt(str) : BigInt((base === 2 ? "0b" : base === 8 ? "0o" : "0x") + str);
}
function parseDate(ctx, c, endChr) {
  let startPtr = ctx.p++, unsafeSeparator;
  if (!isDigit(c) || !isDigit(ctx.s.charCodeAt(ctx.p++)) || !isDigit(ctx.s.charCodeAt(ctx.p++)) || !isDigit(ctx.s.charCodeAt(ctx.p++))) {
    return parseNumber(ctx, ctx.p = startPtr, c, 0, endChr);
  }
  ctx.p += 5;
  if (!isDigit(ctx.s.charCodeAt(ctx.p++)))
    TomlError.x("invalid date-time: date part is malformed", ctx, startPtr);
  if (ctx.p >= ctx.s.length || ((c = ctx.s.charCodeAt(ctx.p)) !== 32 || (unsafeSeparator = true, !isDigit(ctx.s.charCodeAt(ctx.p + 1)))) && c !== 84 && c !== 116) {
    let t2 = ctx.s.slice(startPtr, ctx.p);
    return readDate(ctx, t2, 3, false, startPtr);
  }
  if (ctx.s.charCodeAt(ctx.p += 3) !== 58)
    TomlError.x("invalid date-time: time part is malformed", ctx, startPtr);
  if (ctx.s.charCodeAt(ctx.p += 3) === 58)
    ctx.p += 3;
  if (ctx.s.charCodeAt(ctx.p) === 46)
    while (isDigit(ctx.s.charCodeAt(++ctx.p)))
      ;
  if (c = ctx.s.charCodeAt(ctx.p)) {
    if (c === 90 || c === 122) {
      let t2 = ctx.s.slice(startPtr, ++ctx.p);
      return readDate(ctx, t2, 1, unsafeSeparator, startPtr, "[+00:00]");
    }
    if (c === 43 || c === 45) {
      let t2 = ctx.s.slice(startPtr, ctx.p += 6);
      return readDate(ctx, t2, 1, unsafeSeparator, startPtr, !ctx.ld && "[" + ctx.s.slice(ctx.p - 6, ctx.p) + "]");
    }
  }
  let t = ctx.s.slice(startPtr, ctx.p);
  return readDate(ctx, t, 2, unsafeSeparator, startPtr);
}
function parseTime(ctx, c, endChr) {
  let start = ctx.p;
  if (!isDigit(c) || !isDigit(ctx.s.charCodeAt(++ctx.p))) {
    return parseNumber(ctx, --ctx.p, c, 0, endChr);
  }
  if (ctx.s.charCodeAt(ctx.p += 4) === 58)
    ctx.p += 3;
  if (ctx.s.charCodeAt(ctx.p) === 46)
    while (isDigit(ctx.s.charCodeAt(++ctx.p)))
      ;
  let t = ctx.s.slice(start, ctx.p);
  return readDate(ctx, t, 4, false, start);
}
function readDate(ctx, str, type, unsafeDelim, errPtr, temporalSuffix) {
  if (ctx.ld) {
    let date = new TomlDate(str, type, unsafeDelim);
    if (!date.isValid())
      TomlError.x("invalid date", ctx, errPtr);
    return date;
  }
  try {
    if (temporalSuffix)
      str += temporalSuffix;
    switch (type) {
      case 1:
        return Temporal.ZonedDateTime.from(str);
      case 2:
        return Temporal.PlainDateTime.from(str);
      case 3:
        return Temporal.PlainDate.from(str);
      case 4:
        return Temporal.PlainTime.from(str);
    }
  } catch (e) {
    TomlError.x(e instanceof Error ? e.message : "" + e, ctx, errPtr);
  }
}
var init_extract = __esm({
  "node_modules/smol-toml/dist/extract.js"() {
    init_primitive();
    init_struct();
    init_error();
    init_date();
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
  }
});

// node_modules/smol-toml/dist/util.js
function skipComment(ctx) {
  for (; ctx.p < ctx.s.length; ctx.p++) {
    let c = ctx.s.charCodeAt(ctx.p);
    if (c === 10)
      break;
    if (c === 13 && ctx.s.charCodeAt(ctx.p + 1) === 10) {
      ctx.p++;
      break;
    }
    if (c < 32 && c !== 9 || c === 127) {
      TomlError.x("control characters are not allowed in comments", ctx);
    }
  }
}
function skipVoid(ctx, banNewLines, banComments) {
  let c;
  while (ctx.p < ctx.s.length) {
    while (ctx.p < ctx.s.length && ((c = ctx.s.charCodeAt(ctx.p)) === 32 || c === 9 || !banNewLines && (c === 10 || c === 13 && ctx.s.charCodeAt(ctx.p + 1) === 10)))
      ctx.p++;
    if (banComments || c !== 35)
      break;
    skipComment(ctx);
  }
}
var init_util = __esm({
  "node_modules/smol-toml/dist/util.js"() {
    init_error();
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
  }
});

// node_modules/smol-toml/dist/struct.js
function parseKey(ctx, end = 61) {
  let startPtr;
  let state = 0;
  let parsed = [];
  let sliceStart;
  let c = ctx.s.charCodeAt(startPtr = ctx.p);
  do {
    if (c === end) {
      if (!state)
        TomlError.x("unexpected end of key", ctx);
      if (state === 1)
        parsed.push(ctx.s.slice(sliceStart, ctx.p));
      return ctx.p++, parsed;
    } else if (c === 46) {
      if (!state)
        TomlError.x("illegal empty bare key", ctx);
      if (state === 1)
        parsed.push(ctx.s.slice(sliceStart, ctx.p));
      state = 0;
    } else if (!state && (c === 34 || c === 39)) {
      if (c === ctx.s.charCodeAt(ctx.p + 1) && c === ctx.s.charCodeAt(ctx.p + 2))
        TomlError.x("illegal quoted key: multiline strings are not allowed", ctx);
      parsed.push(parseString(ctx));
      state = 2;
      ctx.p--;
    } else if (c === 32 || c === 9) {
      if (state === 1) {
        parsed.push(ctx.s.slice(sliceStart, ctx.p));
        state = 2;
      }
    } else if (state === 2 || c < 48 && c !== 45 || c > 57 && c < 65 || c > 90 && c < 97 && c !== 95 || c > 122) {
      TomlError.x("illegal character in key", ctx);
    } else if (!state) {
      state = 1;
      sliceStart = ctx.p;
    }
  } while (c = ctx.s.charCodeAt(++ctx.p));
  TomlError.x("incomplete key-value: cannot find end of key", ctx, startPtr);
}
function parseInlineTable(ctx) {
  let startPtr = ctx.p++;
  let res = /* @__PURE__ */ Object.create(null);
  let seen = /* @__PURE__ */ new Set();
  let c;
  while (ctx.p < ctx.s.length) {
    skipVoid(ctx);
    if ((c = ctx.s.charCodeAt(ctx.p)) === 125) {
      ctx.p++;
      return res;
    }
    let k;
    let t = res;
    let hasOwn = false;
    let errPtr = ctx.p;
    let key = parseKey(ctx);
    for (let i = 0; i < key.length; i++) {
      if (i)
        t = hasOwn ? t[k] : t[k] = /* @__PURE__ */ Object.create(null);
      k = key[i];
      if ((hasOwn = Object.hasOwn(t, k)) && (typeof t[k] !== "object" || seen.has(t[k]))) {
        TomlError.x("trying to redefine an already defined value", ctx, errPtr);
      }
      let unsafe = k === "__proto__";
      if (ctx.uk && (unsafe || k === "constructor")) {
        t = ctx.uk !== 1 && TomlError.x("document contains an unsafe property", ctx, errPtr);
        break;
      }
      if (!hasOwn && unsafe) {
        Object.defineProperty(t, k, { enumerable: true, configurable: true, writable: true });
      }
    }
    if (hasOwn) {
      TomlError.x("trying to redefine an already defined value", ctx, errPtr);
    }
    skipVoid(ctx, true, true);
    let value = extractValue(
      ctx,
      125
      /* } */
    );
    if (t && typeof (t[k] = value) === "object")
      seen.add(value);
    skipVoid(ctx);
    if ((c = ctx.s.charCodeAt(ctx.p++)) === 125) {
      return res;
    }
    if (c !== 44)
      TomlError.x("expected comma or end of structure", ctx, ctx.p - 1);
  }
  TomlError.x("unfinished table", ctx, startPtr);
}
function parseArray(ctx) {
  let startPtr = ctx.p++;
  let res = [];
  let c;
  while (ctx.p < ctx.s.length) {
    skipVoid(ctx);
    if ((c = ctx.s.charCodeAt(ctx.p)) === 93) {
      ctx.p++;
      return res;
    }
    res.push(extractValue(
      ctx,
      93
      /* ] */
    ));
    skipVoid(ctx);
    if ((c = ctx.s.charCodeAt(ctx.p++)) === 93) {
      return res;
    }
    if (c !== 44)
      TomlError.x("expected comma or end of structure", ctx, ctx.p - 1);
  }
  TomlError.x("unfinished array", ctx, startPtr);
}
var init_struct = __esm({
  "node_modules/smol-toml/dist/struct.js"() {
    init_primitive();
    init_extract();
    init_util();
    init_error();
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
  }
});

// node_modules/smol-toml/dist/parse.js
function peekTable(ctx, key, table, meta, type) {
  let t = table;
  let m = meta;
  let k;
  let hasOwn = false;
  let state;
  for (let i = 0; i < key.length; i++) {
    if (i) {
      t = hasOwn ? t[k] : t[k] = /* @__PURE__ */ Object.create(null);
      m = (state = m[k]).c;
      if (type === 0 && (state.t === 1 || state.t === 2)) {
        return null;
      }
      if (state.t === 2) {
        let l = t.length - 1;
        t = t[l];
        m = m[l].c;
      }
    }
    k = key[i];
    if ((hasOwn = Object.hasOwn(t, k)) && m[k]?.t === 0 && m[k]?.d) {
      return null;
    }
    if (!hasOwn) {
      let unsafe = k === "__proto__";
      if (ctx.uk && (unsafe || k === "constructor"))
        return false;
      if (unsafe) {
        Object.defineProperty(t, k, { enumerable: true, configurable: true, writable: true });
        Object.defineProperty(m, k, { enumerable: true, configurable: true, writable: true });
      }
      m[k] = {
        t: i < key.length - 1 && type === 2 ? 3 : type,
        d: false,
        i: 0,
        c: /* @__PURE__ */ Object.create(null)
      };
    }
  }
  state = m[k];
  if (state.t !== type && !(type === 1 && state.t === 3)) {
    return null;
  }
  if (type === 2) {
    if (!state.d) {
      state.d = true;
      t[k] = [];
    }
    t[k].push(t = /* @__PURE__ */ Object.create(null));
    state.c[state.i++] = state = { t: 1, d: false, i: 0, c: /* @__PURE__ */ Object.create(null) };
  }
  if (state.d) {
    return null;
  }
  state.d = true;
  if (type === 1) {
    t = hasOwn ? t[k] : t[k] = /* @__PURE__ */ Object.create(null);
  } else if (type === 0 && hasOwn) {
    return null;
  }
  return [k, t, state.c];
}
function validateTablePeek(ctx, peek, ptr) {
  if (peek === null || ctx.uk === 2)
    TomlError.x(peek === null ? "trying to redefine an already defined table or value" : "document contains an unsafe property", ctx, ptr);
}
function parse(toml, options2 = {}) {
  let ctx = {
    s: toml,
    p: 0,
    d: options2.maxDepth ?? 1e3,
    bi: options2.integersAsBigInt ?? false,
    ld: options2.useLegacyDate ?? true,
    uk: options2.unsafeKeyBehaviour === "throw" ? 2 : options2.unsafeKeyBehaviour === "drop" ? 1 : 0
  };
  let res = /* @__PURE__ */ Object.create(null);
  let meta = /* @__PURE__ */ Object.create(null);
  let tmp;
  let skipping = false;
  let tbl = res;
  let m = meta;
  if (toml.charCodeAt(0) === 65279)
    ctx.p++;
  skipVoid(ctx);
  while (ctx.p < toml.length) {
    if (toml.charCodeAt(ctx.p) === 91) {
      let isTableArray = toml.charCodeAt(++ctx.p) === 91;
      tmp = ctx.p += +isTableArray;
      skipping = false;
      let k = parseKey(
        ctx,
        93
        /* ] */
      );
      if (isTableArray) {
        if (toml.charCodeAt(ctx.p) !== 93) {
          TomlError.x("expected end of table array declaration", ctx);
        }
        ctx.p++;
      }
      let p = peekTable(
        ctx,
        k,
        res,
        meta,
        isTableArray ? 2 : 1
        /* Type.EXPLICIT */
      );
      if (!p) {
        validateTablePeek(ctx, p, tmp);
        skipping = true;
      } else {
        m = p[2];
        tbl = p[1];
      }
    } else {
      tmp = ctx.p;
      let k = parseKey(ctx);
      let p = peekTable(
        ctx,
        k,
        tbl,
        m,
        0
        /* Type.DOTTED */
      );
      if (!p && !skipping)
        validateTablePeek(ctx, p, tmp);
      skipVoid(ctx, true, true);
      let v = extractValue(ctx, void 0);
      if (p && !skipping)
        p[1][p[0]] = v;
    }
    skipVoid(ctx, true);
    if (ctx.p < toml.length && (tmp = toml.charCodeAt(ctx.p)) !== 10 && (tmp !== 13 || toml.charCodeAt(ctx.p + 1) !== 10)) {
      TomlError.x("each key-value declaration must be followed by an end-of-line", ctx);
    }
    skipVoid(ctx);
  }
  return res;
}
var init_parse = __esm({
  "node_modules/smol-toml/dist/parse.js"() {
    init_struct();
    init_extract();
    init_util();
    init_error();
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
  }
});

// node_modules/smol-toml/dist/stringify.js
function extendedTypeOf(obj) {
  let type = typeof obj;
  if (type === "object") {
    if (Array.isArray(obj))
      return "array";
    if (typeof obj.getUTCDate === "function" && obj instanceof Date)
      return "date";
    if (globalThis.Temporal) {
      if (obj.until) {
        if (obj instanceof Temporal.ZonedDateTime)
          return "temporal/tz+uc";
        if (obj instanceof Temporal.PlainDateTime || obj instanceof Temporal.PlainDate)
          return "temporal/uc";
        if (obj instanceof Temporal.PlainTime || obj instanceof Temporal.Instant)
          return "temporal";
        if (obj instanceof Temporal.PlainYearMonth)
          return "temporal/x";
      } else if (obj.toPlainDate && obj instanceof Temporal.PlainMonthDay || obj.negated && obj instanceof Temporal.Duration) {
        return "temporal/x";
      }
    }
  }
  return type;
}
function isArrayOfTables(obj) {
  for (let i = 0; i < obj.length; i++) {
    if (extendedTypeOf(obj[i]) !== "object")
      return false;
  }
  return obj.length != 0;
}
function formatWellFormedStringUnchecked(s) {
  return JSON.stringify(s).replaceAll("\x7F", "\\u007f");
}
function formatString(s) {
  return formatWellFormedStringUnchecked(HAS_WELLFORMED ? s.toWellFormed() : s);
}
function formatKey(s) {
  if (BARE_KEY.test(s))
    return s;
  if (HAS_WELLFORMED && !s.isWellFormed())
    throw new RangeError("key contains illegal lone surrogates");
  return formatWellFormedStringUnchecked(s);
}
function stringifyValue(val, type, depth, numberAsFloat, strictTemporal) {
  if (depth === 0) {
    throw new Error("Could not stringify the object: maximum object depth exceeded");
  }
  switch (type) {
    // @ts-expect-error -- intentional fallthrough case
    case "number":
      if (isNaN(val))
        return "nan";
      if (val === Infinity)
        return "inf";
      if (val === -Infinity)
        return "-inf";
      if (Number.isInteger(val) && (numberAsFloat || !Number.isSafeInteger(val)))
        return val.toFixed(1);
    case "bigint":
    case "boolean":
    case "temporal":
      return val.toString();
    case "string":
      return formatString(val);
    case "date":
      if (isNaN(val.getTime()))
        throw new TypeError("cannot serialize invalid date");
      return val.toISOString();
    case "object":
      return stringifyInlineTable(val, depth, numberAsFloat, strictTemporal);
    case "array":
      return stringifyArray(val, depth, numberAsFloat, strictTemporal);
    // @ts-expect-error -- intentional fallthrough case
    case "temporal/tz+uc":
      if (strictTemporal) {
        let tz = val.timeZoneId;
        let tzc = tz.charCodeAt(0);
        if (
          // Classic offset
          tzc !== 43 && tzc !== 45 && // Fast pre-check pass; see below for the actually accepted values
          (tzc !== 85 && tzc !== 71 && tzc !== 90 && tzc !== 69 || // UTC and its aliases; Temporal implementations don't all canonicalise unfortunately
          tz !== "UTC" && tz !== "UCT" && tz !== "Universal" && tz !== "Zulu" && // GMT is a TZ but it's for all intents and purposes equivalent to UTC. Safe to downgrade.
          !tz.startsWith("GMT") && tz !== "Greenwich" && // Etc/* are all safe to downgrade to offset (either UTC, GMT, or offset)
          !tz.startsWith("Etc/"))
        ) {
          throw new TypeError("Temporal objects with an IANA timezone are not allowed in Temporal strict mode");
        }
      }
    case "temporal/uc":
      if (strictTemporal && val.calendarId !== "iso8601")
        throw new TypeError("Temporal objects with a non-default calendar are not allowed in Temporal strict mode");
      return val.toString({
        calendarName: "never",
        timeZoneName: "never"
      });
    case "temporal/x":
      throw new TypeError("Unsupported " + val[Symbol.toStringTag]);
  }
}
function stringifyInlineTable(obj, depth, numberAsFloat, strictTemporal) {
  let keys = Object.keys(obj);
  if (keys.length === 0)
    return "{}";
  let res = "{ ";
  for (let i = 0; i < keys.length; i++) {
    let k = keys[i];
    if (i)
      res += ", ";
    res += formatKey(k) + " = " + stringifyValue(obj[k], extendedTypeOf(obj[k]), depth - 1, numberAsFloat, strictTemporal);
  }
  return res + " }";
}
function stringifyArray(array, depth, numberAsFloat, strictTemporal) {
  if (array.length === 0)
    return "[]";
  let res = "[ ";
  for (let i = 0; i < array.length; i++) {
    if (i)
      res += ", ";
    if (array[i] === null || array[i] === void 0) {
      throw new TypeError("arrays cannot contain null or undefined values");
    }
    res += stringifyValue(array[i], extendedTypeOf(array[i]), depth - 1, numberAsFloat, strictTemporal);
  }
  return res + " ]";
}
function stringifyArrayTable(array, key, depth, numberAsFloat, strictTemporal) {
  if (depth === 0) {
    throw new Error("Could not stringify the object: maximum object depth exceeded");
  }
  let res = "";
  for (let i = 0; i < array.length; i++) {
    res += `${res && "\n"}[[${key}]]
`;
    res += stringifyTable(0, array[i], key, depth, numberAsFloat, strictTemporal);
  }
  return res;
}
function stringifyTable(tableKey, obj, prefix, depth, numberAsFloat, strictTemporal) {
  if (depth === 0) {
    throw new Error("Could not stringify the object: maximum object depth exceeded");
  }
  let preamble = "";
  let tables = "";
  let keys = Object.keys(obj);
  for (let i = 0; i < keys.length; i++) {
    let k = keys[i];
    if (obj[k] !== null && obj[k] !== void 0) {
      let type = extendedTypeOf(obj[k]);
      if (type === "symbol" || type === "function") {
        throw new TypeError(`cannot serialize values of type '${type}'`);
      }
      let key = formatKey(k);
      if (type === "array" && isArrayOfTables(obj[k])) {
        tables += (tables && "\n") + stringifyArrayTable(obj[k], prefix ? `${prefix}.${key}` : key, depth - 1, numberAsFloat, strictTemporal);
      } else if (type === "object") {
        let tblKey = prefix ? `${prefix}.${key}` : key;
        tables += (tables && "\n") + stringifyTable(tblKey, obj[k], tblKey, depth - 1, numberAsFloat, strictTemporal);
      } else {
        preamble += key;
        preamble += " = ";
        preamble += stringifyValue(obj[k], type, depth, numberAsFloat, strictTemporal);
        preamble += "\n";
      }
    }
  }
  if (tableKey && (preamble || !tables))
    preamble = preamble ? `[${tableKey}]
${preamble}` : `[${tableKey}]`;
  return preamble && tables ? `${preamble}
${tables}` : preamble || tables;
}
function stringify(obj, { maxDepth = 1e3, numbersAsFloat = false, strictTemporal = false } = {}) {
  if (extendedTypeOf(obj) !== "object") {
    throw new TypeError("stringify can only be called with an object");
  }
  let str = stringifyTable(0, obj, "", maxDepth, numbersAsFloat, strictTemporal);
  if (str[str.length - 1] !== "\n")
    return str + "\n";
  return str;
}
var BARE_KEY, HAS_WELLFORMED;
var init_stringify = __esm({
  "node_modules/smol-toml/dist/stringify.js"() {
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
    BARE_KEY = /^[a-z0-9-_]+$/i;
    HAS_WELLFORMED = !!"".isWellFormed;
  }
});

// node_modules/smol-toml/dist/index.js
var dist_exports = {};
__export(dist_exports, {
  TomlDate: () => TomlDate,
  TomlError: () => TomlError,
  default: () => dist_default,
  parse: () => parse,
  stringify: () => stringify
});
var dist_default;
var init_dist = __esm({
  "node_modules/smol-toml/dist/index.js"() {
    init_parse();
    init_stringify();
    init_date();
    init_error();
    /*!
     * Copyright (c) Squirrel Chat et al., All rights reserved.
     * SPDX-License-Identifier: BSD-3-Clause
     *
     * Redistribution and use in source and binary forms, with or without
     * modification, are permitted provided that the following conditions are met:
     *
     * 1. Redistributions of source code must retain the above copyright notice, this
     *    list of conditions and the following disclaimer.
     * 2. Redistributions in binary form must reproduce the above copyright notice,
     *    this list of conditions and the following disclaimer in the
     *    documentation and/or other materials provided with the distribution.
     * 3. Neither the name of the copyright holder nor the names of its contributors
     *    may be used to endorse or promote products derived from this software without
     *    specific prior written permission.
     *
     * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
     * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
     * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
     * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
     * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
     * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
     * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
     * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
     * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
     * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
     */
    dist_default = { parse, stringify, TomlDate, TomlError };
  }
});

// node_modules/dns-packet/types.js
var require_types = __commonJS({
  "node_modules/dns-packet/types.js"(exports) {
    "use strict";
    exports.toString = function(type) {
      switch (type) {
        case 1:
          return "A";
        case 10:
          return "NULL";
        case 28:
          return "AAAA";
        case 18:
          return "AFSDB";
        case 42:
          return "APL";
        case 257:
          return "CAA";
        case 60:
          return "CDNSKEY";
        case 59:
          return "CDS";
        case 37:
          return "CERT";
        case 5:
          return "CNAME";
        case 49:
          return "DHCID";
        case 32769:
          return "DLV";
        case 39:
          return "DNAME";
        case 48:
          return "DNSKEY";
        case 43:
          return "DS";
        case 55:
          return "HIP";
        case 13:
          return "HINFO";
        case 45:
          return "IPSECKEY";
        case 25:
          return "KEY";
        case 36:
          return "KX";
        case 29:
          return "LOC";
        case 15:
          return "MX";
        case 35:
          return "NAPTR";
        case 2:
          return "NS";
        case 47:
          return "NSEC";
        case 50:
          return "NSEC3";
        case 51:
          return "NSEC3PARAM";
        case 12:
          return "PTR";
        case 46:
          return "RRSIG";
        case 17:
          return "RP";
        case 24:
          return "SIG";
        case 6:
          return "SOA";
        case 99:
          return "SPF";
        case 33:
          return "SRV";
        case 44:
          return "SSHFP";
        case 32768:
          return "TA";
        case 249:
          return "TKEY";
        case 52:
          return "TLSA";
        case 250:
          return "TSIG";
        case 16:
          return "TXT";
        case 252:
          return "AXFR";
        case 251:
          return "IXFR";
        case 41:
          return "OPT";
        case 255:
          return "ANY";
      }
      return "UNKNOWN_" + type;
    };
    exports.toType = function(name) {
      switch (name.toUpperCase()) {
        case "A":
          return 1;
        case "NULL":
          return 10;
        case "AAAA":
          return 28;
        case "AFSDB":
          return 18;
        case "APL":
          return 42;
        case "CAA":
          return 257;
        case "CDNSKEY":
          return 60;
        case "CDS":
          return 59;
        case "CERT":
          return 37;
        case "CNAME":
          return 5;
        case "DHCID":
          return 49;
        case "DLV":
          return 32769;
        case "DNAME":
          return 39;
        case "DNSKEY":
          return 48;
        case "DS":
          return 43;
        case "HIP":
          return 55;
        case "HINFO":
          return 13;
        case "IPSECKEY":
          return 45;
        case "KEY":
          return 25;
        case "KX":
          return 36;
        case "LOC":
          return 29;
        case "MX":
          return 15;
        case "NAPTR":
          return 35;
        case "NS":
          return 2;
        case "NSEC":
          return 47;
        case "NSEC3":
          return 50;
        case "NSEC3PARAM":
          return 51;
        case "PTR":
          return 12;
        case "RRSIG":
          return 46;
        case "RP":
          return 17;
        case "SIG":
          return 24;
        case "SOA":
          return 6;
        case "SPF":
          return 99;
        case "SRV":
          return 33;
        case "SSHFP":
          return 44;
        case "TA":
          return 32768;
        case "TKEY":
          return 249;
        case "TLSA":
          return 52;
        case "TSIG":
          return 250;
        case "TXT":
          return 16;
        case "AXFR":
          return 252;
        case "IXFR":
          return 251;
        case "OPT":
          return 41;
        case "ANY":
          return 255;
        case "*":
          return 255;
      }
      if (name.toUpperCase().startsWith("UNKNOWN_")) return parseInt(name.slice(8));
      return 0;
    };
  }
});

// node_modules/dns-packet/rcodes.js
var require_rcodes = __commonJS({
  "node_modules/dns-packet/rcodes.js"(exports) {
    "use strict";
    exports.toString = function(rcode) {
      switch (rcode) {
        case 0:
          return "NOERROR";
        case 1:
          return "FORMERR";
        case 2:
          return "SERVFAIL";
        case 3:
          return "NXDOMAIN";
        case 4:
          return "NOTIMP";
        case 5:
          return "REFUSED";
        case 6:
          return "YXDOMAIN";
        case 7:
          return "YXRRSET";
        case 8:
          return "NXRRSET";
        case 9:
          return "NOTAUTH";
        case 10:
          return "NOTZONE";
        case 11:
          return "RCODE_11";
        case 12:
          return "RCODE_12";
        case 13:
          return "RCODE_13";
        case 14:
          return "RCODE_14";
        case 15:
          return "RCODE_15";
      }
      return "RCODE_" + rcode;
    };
    exports.toRcode = function(code) {
      switch (code.toUpperCase()) {
        case "NOERROR":
          return 0;
        case "FORMERR":
          return 1;
        case "SERVFAIL":
          return 2;
        case "NXDOMAIN":
          return 3;
        case "NOTIMP":
          return 4;
        case "REFUSED":
          return 5;
        case "YXDOMAIN":
          return 6;
        case "YXRRSET":
          return 7;
        case "NXRRSET":
          return 8;
        case "NOTAUTH":
          return 9;
        case "NOTZONE":
          return 10;
        case "RCODE_11":
          return 11;
        case "RCODE_12":
          return 12;
        case "RCODE_13":
          return 13;
        case "RCODE_14":
          return 14;
        case "RCODE_15":
          return 15;
      }
      return 0;
    };
  }
});

// node_modules/dns-packet/opcodes.js
var require_opcodes = __commonJS({
  "node_modules/dns-packet/opcodes.js"(exports) {
    "use strict";
    exports.toString = function(opcode) {
      switch (opcode) {
        case 0:
          return "QUERY";
        case 1:
          return "IQUERY";
        case 2:
          return "STATUS";
        case 3:
          return "OPCODE_3";
        case 4:
          return "NOTIFY";
        case 5:
          return "UPDATE";
        case 6:
          return "OPCODE_6";
        case 7:
          return "OPCODE_7";
        case 8:
          return "OPCODE_8";
        case 9:
          return "OPCODE_9";
        case 10:
          return "OPCODE_10";
        case 11:
          return "OPCODE_11";
        case 12:
          return "OPCODE_12";
        case 13:
          return "OPCODE_13";
        case 14:
          return "OPCODE_14";
        case 15:
          return "OPCODE_15";
      }
      return "OPCODE_" + opcode;
    };
    exports.toOpcode = function(code) {
      switch (code.toUpperCase()) {
        case "QUERY":
          return 0;
        case "IQUERY":
          return 1;
        case "STATUS":
          return 2;
        case "OPCODE_3":
          return 3;
        case "NOTIFY":
          return 4;
        case "UPDATE":
          return 5;
        case "OPCODE_6":
          return 6;
        case "OPCODE_7":
          return 7;
        case "OPCODE_8":
          return 8;
        case "OPCODE_9":
          return 9;
        case "OPCODE_10":
          return 10;
        case "OPCODE_11":
          return 11;
        case "OPCODE_12":
          return 12;
        case "OPCODE_13":
          return 13;
        case "OPCODE_14":
          return 14;
        case "OPCODE_15":
          return 15;
      }
      return 0;
    };
  }
});

// node_modules/dns-packet/classes.js
var require_classes = __commonJS({
  "node_modules/dns-packet/classes.js"(exports) {
    "use strict";
    exports.toString = function(klass) {
      switch (klass) {
        case 1:
          return "IN";
        case 2:
          return "CS";
        case 3:
          return "CH";
        case 4:
          return "HS";
        case 255:
          return "ANY";
      }
      return "UNKNOWN_" + klass;
    };
    exports.toClass = function(name) {
      switch (name.toUpperCase()) {
        case "IN":
          return 1;
        case "CS":
          return 2;
        case "CH":
          return 3;
        case "HS":
          return 4;
        case "ANY":
          return 255;
      }
      return 0;
    };
  }
});

// node_modules/dns-packet/optioncodes.js
var require_optioncodes = __commonJS({
  "node_modules/dns-packet/optioncodes.js"(exports) {
    "use strict";
    exports.toString = function(type) {
      switch (type) {
        // list at
        // https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml#dns-parameters-11
        case 1:
          return "LLQ";
        case 2:
          return "UL";
        case 3:
          return "NSID";
        case 5:
          return "DAU";
        case 6:
          return "DHU";
        case 7:
          return "N3U";
        case 8:
          return "CLIENT_SUBNET";
        case 9:
          return "EXPIRE";
        case 10:
          return "COOKIE";
        case 11:
          return "TCP_KEEPALIVE";
        case 12:
          return "PADDING";
        case 13:
          return "CHAIN";
        case 14:
          return "KEY_TAG";
        case 26946:
          return "DEVICEID";
      }
      if (type < 0) {
        return null;
      }
      return `OPTION_${type}`;
    };
    exports.toCode = function(name) {
      if (typeof name === "number") {
        return name;
      }
      if (!name) {
        return -1;
      }
      switch (name.toUpperCase()) {
        case "OPTION_0":
          return 0;
        case "LLQ":
          return 1;
        case "UL":
          return 2;
        case "NSID":
          return 3;
        case "OPTION_4":
          return 4;
        case "DAU":
          return 5;
        case "DHU":
          return 6;
        case "N3U":
          return 7;
        case "CLIENT_SUBNET":
          return 8;
        case "EXPIRE":
          return 9;
        case "COOKIE":
          return 10;
        case "TCP_KEEPALIVE":
          return 11;
        case "PADDING":
          return 12;
        case "CHAIN":
          return 13;
        case "KEY_TAG":
          return 14;
        case "DEVICEID":
          return 26946;
        case "OPTION_65535":
          return 65535;
      }
      const m = name.match(/_(\d+)$/);
      if (m) {
        return parseInt(m[1], 10);
      }
      return -1;
    };
  }
});

// node_modules/@leichtgewicht/ip-codec/index.cjs
var require_ip_codec = __commonJS({
  "node_modules/@leichtgewicht/ip-codec/index.cjs"(exports, module) {
    var ipCodec = (function(exports2) {
      "use strict";
      Object.defineProperty(exports2, "__esModule", {
        value: true
      });
      exports2.decode = decode;
      exports2.encode = encode;
      exports2.familyOf = familyOf;
      exports2.name = void 0;
      exports2.sizeOf = sizeOf;
      exports2.v6 = exports2.v4 = void 0;
      const v4Regex = /^(\d{1,3}\.){3,3}\d{1,3}$/;
      const v4Size = 4;
      const v6Regex = /^(::)?(((\d{1,3}\.){3}(\d{1,3}){1})?([0-9a-f]){0,4}:{0,2}){1,8}(::)?$/i;
      const v6Size = 16;
      const v4 = {
        name: "v4",
        size: v4Size,
        isFormat: (ip) => v4Regex.test(ip),
        encode(ip, buff, offset) {
          offset = ~~offset;
          buff = buff || new Uint8Array(offset + v4Size);
          const max = ip.length;
          let n = 0;
          for (let i = 0; i < max; ) {
            const c = ip.charCodeAt(i++);
            if (c === 46) {
              buff[offset++] = n;
              n = 0;
            } else {
              n = n * 10 + (c - 48);
            }
          }
          buff[offset] = n;
          return buff;
        },
        decode(buff, offset) {
          offset = ~~offset;
          return `${buff[offset++]}.${buff[offset++]}.${buff[offset++]}.${buff[offset]}`;
        }
      };
      exports2.v4 = v4;
      const v6 = {
        name: "v6",
        size: v6Size,
        isFormat: (ip) => ip.length > 0 && v6Regex.test(ip),
        encode(ip, buff, offset) {
          offset = ~~offset;
          let end = offset + v6Size;
          let fill = -1;
          let hexN = 0;
          let decN = 0;
          let prevColon = true;
          let useDec = false;
          buff = buff || new Uint8Array(offset + v6Size);
          for (let i = 0; i < ip.length; i++) {
            let c = ip.charCodeAt(i);
            if (c === 58) {
              if (prevColon) {
                if (fill !== -1) {
                  if (offset < end) buff[offset] = 0;
                  if (offset < end - 1) buff[offset + 1] = 0;
                  offset += 2;
                } else if (offset < end) {
                  fill = offset;
                }
              } else {
                if (useDec === true) {
                  if (offset < end) buff[offset] = decN;
                  offset++;
                } else {
                  if (offset < end) buff[offset] = hexN >> 8;
                  if (offset < end - 1) buff[offset + 1] = hexN & 255;
                  offset += 2;
                }
                hexN = 0;
                decN = 0;
              }
              prevColon = true;
              useDec = false;
            } else if (c === 46) {
              if (offset < end) buff[offset] = decN;
              offset++;
              decN = 0;
              hexN = 0;
              prevColon = false;
              useDec = true;
            } else {
              prevColon = false;
              if (c >= 97) {
                c -= 87;
              } else if (c >= 65) {
                c -= 55;
              } else {
                c -= 48;
                decN = decN * 10 + c;
              }
              hexN = (hexN << 4) + c;
            }
          }
          if (prevColon === false) {
            if (useDec === true) {
              if (offset < end) buff[offset] = decN;
              offset++;
            } else {
              if (offset < end) buff[offset] = hexN >> 8;
              if (offset < end - 1) buff[offset + 1] = hexN & 255;
              offset += 2;
            }
          } else if (fill === 0) {
            if (offset < end) buff[offset] = 0;
            if (offset < end - 1) buff[offset + 1] = 0;
            offset += 2;
          } else if (fill !== -1) {
            offset += 2;
            for (let i = Math.min(offset - 1, end - 1); i >= fill + 2; i--) {
              buff[i] = buff[i - 2];
            }
            buff[fill] = 0;
            buff[fill + 1] = 0;
            fill = offset;
          }
          if (fill !== offset && fill !== -1) {
            if (offset > end - 2) {
              offset = end - 2;
            }
            while (end > fill) {
              buff[--end] = offset < end && offset > fill ? buff[--offset] : 0;
            }
          } else {
            while (offset < end) {
              buff[offset++] = 0;
            }
          }
          return buff;
        },
        decode(buff, offset) {
          offset = ~~offset;
          let result = "";
          for (let i = 0; i < v6Size; i += 2) {
            if (i !== 0) {
              result += ":";
            }
            result += (buff[offset + i] << 8 | buff[offset + i + 1]).toString(16);
          }
          return result.replace(/(^|:)0(:0)*:0(:|$)/, "$1::$3").replace(/:{3,4}/, "::");
        }
      };
      exports2.v6 = v6;
      const name = "ip";
      exports2.name = name;
      function sizeOf(ip) {
        if (v4.isFormat(ip)) return v4.size;
        if (v6.isFormat(ip)) return v6.size;
        throw Error(`Invalid ip address: ${ip}`);
      }
      function familyOf(string) {
        return sizeOf(string) === v4.size ? 1 : 2;
      }
      function encode(ip, buff, offset) {
        offset = ~~offset;
        const size = sizeOf(ip);
        if (typeof buff === "function") {
          buff = buff(offset + size);
        }
        if (size === v4.size) {
          return v4.encode(ip, buff, offset);
        }
        return v6.encode(ip, buff, offset);
      }
      function decode(buff, offset, length) {
        offset = ~~offset;
        length = length || buff.length - offset;
        if (length === v4.size) {
          return v4.decode(buff, offset, length);
        }
        if (length === v6.size) {
          return v6.decode(buff, offset, length);
        }
        throw Error(`Invalid buffer size needs to be ${v4.size} for v4 or ${v6.size} for v6.`);
      }
      return "default" in exports2 ? exports2.default : exports2;
    })({});
    if (typeof define === "function" && define.amd) define([], function() {
      return ipCodec;
    });
    else if (typeof module === "object" && typeof exports === "object") module.exports = ipCodec;
  }
});

// node_modules/dns-packet/index.js
var require_dns_packet = __commonJS({
  "node_modules/dns-packet/index.js"(exports) {
    "use strict";
    var Buffer2 = __require("buffer").Buffer;
    var types = require_types();
    var rcodes = require_rcodes();
    var opcodes = require_opcodes();
    var classes = require_classes();
    var optioncodes = require_optioncodes();
    var ip = require_ip_codec();
    var QUERY_FLAG = 0;
    var RESPONSE_FLAG = 1 << 15;
    var FLUSH_MASK = 1 << 15;
    var NOT_FLUSH_MASK = ~FLUSH_MASK;
    var QU_MASK = 1 << 15;
    var NOT_QU_MASK = ~QU_MASK;
    var name = exports.name = {};
    name.encode = function(str, buf, offset, { mail = false } = {}) {
      if (!buf) buf = Buffer2.alloc(name.encodingLength(str));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const n = str.replace(/^\.|\.$/gm, "");
      if (n.length) {
        let list = [];
        if (mail) {
          let localPart = "";
          n.split(".").forEach((label) => {
            if (label.endsWith("\\")) {
              localPart += (localPart.length ? "." : "") + label.slice(0, -1);
            } else {
              if (list.length === 0 && localPart.length) {
                list.push(localPart + "." + label);
              } else {
                list.push(label);
              }
            }
          });
        } else {
          list = n.split(".");
        }
        for (let i = 0; i < list.length; i++) {
          const len = buf.write(list[i], offset + 1);
          buf[offset] = len;
          offset += len + 1;
        }
      }
      buf[offset++] = 0;
      name.encode.bytes = offset - oldOffset;
      return buf;
    };
    name.encode.bytes = 0;
    name.decode = function(buf, offset, { mail = false } = {}) {
      if (!offset) offset = 0;
      const list = [];
      let oldOffset = offset;
      let totalLength = 0;
      let consumedBytes = 0;
      let jumped = false;
      while (true) {
        if (offset >= buf.length) {
          throw new Error("Cannot decode name (buffer overflow)");
        }
        const len = buf[offset++];
        consumedBytes += jumped ? 0 : 1;
        if (len === 0) {
          break;
        } else if ((len & 192) === 0) {
          if (offset + len > buf.length) {
            throw new Error("Cannot decode name (buffer overflow)");
          }
          totalLength += len + 1;
          if (totalLength > 254) {
            throw new Error("Cannot decode name (name too long)");
          }
          let label = buf.toString("utf-8", offset, offset + len);
          if (mail) {
            label = label.replace(/\./g, "\\.");
          }
          list.push(label);
          offset += len;
          consumedBytes += jumped ? 0 : len;
        } else if ((len & 192) === 192) {
          if (offset + 1 > buf.length) {
            throw new Error("Cannot decode name (buffer overflow)");
          }
          const jumpOffset = buf.readUInt16BE(offset - 1) - 49152;
          if (jumpOffset >= oldOffset) {
            throw new Error("Cannot decode name (bad pointer)");
          }
          offset = jumpOffset;
          oldOffset = jumpOffset;
          consumedBytes += jumped ? 0 : 1;
          jumped = true;
        } else {
          throw new Error("Cannot decode name (bad label)");
        }
      }
      name.decode.bytes = consumedBytes;
      return list.length === 0 ? "." : list.join(".");
    };
    name.decode.bytes = 0;
    name.encodingLength = function(n) {
      if (n === "." || n === "..") return 1;
      return Buffer2.byteLength(n.replace(/^\.|\.$/gm, "")) + 2;
    };
    var string = {};
    string.encode = function(s, buf, offset) {
      if (!buf) buf = Buffer2.alloc(string.encodingLength(s));
      if (!offset) offset = 0;
      const len = buf.write(s, offset + 1);
      buf[offset] = len;
      string.encode.bytes = len + 1;
      return buf;
    };
    string.encode.bytes = 0;
    string.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf[offset];
      const s = buf.toString("utf-8", offset + 1, offset + 1 + len);
      string.decode.bytes = len + 1;
      return s;
    };
    string.decode.bytes = 0;
    string.encodingLength = function(s) {
      return Buffer2.byteLength(s) + 1;
    };
    var header = {};
    header.encode = function(h, buf, offset) {
      if (!buf) buf = header.encodingLength(h);
      if (!offset) offset = 0;
      const flags = (h.flags || 0) & 32767;
      const type = h.type === "response" ? RESPONSE_FLAG : QUERY_FLAG;
      buf.writeUInt16BE(h.id || 0, offset);
      buf.writeUInt16BE(flags | type, offset + 2);
      buf.writeUInt16BE(h.questions.length, offset + 4);
      buf.writeUInt16BE(h.answers.length, offset + 6);
      buf.writeUInt16BE(h.authorities.length, offset + 8);
      buf.writeUInt16BE(h.additionals.length, offset + 10);
      return buf;
    };
    header.encode.bytes = 12;
    header.decode = function(buf, offset) {
      if (!offset) offset = 0;
      if (buf.length < 12) throw new Error("Header must be 12 bytes");
      const flags = buf.readUInt16BE(offset + 2);
      return {
        id: buf.readUInt16BE(offset),
        type: flags & RESPONSE_FLAG ? "response" : "query",
        flags: flags & 32767,
        flag_qr: (flags >> 15 & 1) === 1,
        opcode: opcodes.toString(flags >> 11 & 15),
        flag_aa: (flags >> 10 & 1) === 1,
        flag_tc: (flags >> 9 & 1) === 1,
        flag_rd: (flags >> 8 & 1) === 1,
        flag_ra: (flags >> 7 & 1) === 1,
        flag_z: (flags >> 6 & 1) === 1,
        flag_ad: (flags >> 5 & 1) === 1,
        flag_cd: (flags >> 4 & 1) === 1,
        rcode: rcodes.toString(flags & 15),
        questions: new Array(buf.readUInt16BE(offset + 4)),
        answers: new Array(buf.readUInt16BE(offset + 6)),
        authorities: new Array(buf.readUInt16BE(offset + 8)),
        additionals: new Array(buf.readUInt16BE(offset + 10))
      };
    };
    header.decode.bytes = 12;
    header.encodingLength = function() {
      return 12;
    };
    var runknown = exports.unknown = {};
    runknown.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(runknown.encodingLength(data));
      if (!offset) offset = 0;
      buf.writeUInt16BE(data.length, offset);
      data.copy(buf, offset + 2);
      runknown.encode.bytes = data.length + 2;
      return buf;
    };
    runknown.encode.bytes = 0;
    runknown.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf.readUInt16BE(offset);
      const data = buf.slice(offset + 2, offset + 2 + len);
      runknown.decode.bytes = len + 2;
      return data;
    };
    runknown.decode.bytes = 0;
    runknown.encodingLength = function(data) {
      return data.length + 2;
    };
    var rns = exports.ns = {};
    rns.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rns.encodingLength(data));
      if (!offset) offset = 0;
      name.encode(data, buf, offset + 2);
      buf.writeUInt16BE(name.encode.bytes, offset);
      rns.encode.bytes = name.encode.bytes + 2;
      return buf;
    };
    rns.encode.bytes = 0;
    rns.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf.readUInt16BE(offset);
      const dd = name.decode(buf, offset + 2);
      rns.decode.bytes = len + 2;
      return dd;
    };
    rns.decode.bytes = 0;
    rns.encodingLength = function(data) {
      return name.encodingLength(data) + 2;
    };
    var rsoa = exports.soa = {};
    rsoa.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rsoa.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      name.encode(data.mname, buf, offset);
      offset += name.encode.bytes;
      name.encode(data.rname, buf, offset, { mail: true });
      offset += name.encode.bytes;
      buf.writeUInt32BE(data.serial || 0, offset);
      offset += 4;
      buf.writeUInt32BE(data.refresh || 0, offset);
      offset += 4;
      buf.writeUInt32BE(data.retry || 0, offset);
      offset += 4;
      buf.writeUInt32BE(data.expire || 0, offset);
      offset += 4;
      buf.writeUInt32BE(data.minimum || 0, offset);
      offset += 4;
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rsoa.encode.bytes = offset - oldOffset;
      return buf;
    };
    rsoa.encode.bytes = 0;
    rsoa.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.mname = name.decode(buf, offset);
      offset += name.decode.bytes;
      data.rname = name.decode(buf, offset, { mail: true });
      offset += name.decode.bytes;
      data.serial = buf.readUInt32BE(offset);
      offset += 4;
      data.refresh = buf.readUInt32BE(offset);
      offset += 4;
      data.retry = buf.readUInt32BE(offset);
      offset += 4;
      data.expire = buf.readUInt32BE(offset);
      offset += 4;
      data.minimum = buf.readUInt32BE(offset);
      offset += 4;
      rsoa.decode.bytes = offset - oldOffset;
      return data;
    };
    rsoa.decode.bytes = 0;
    rsoa.encodingLength = function(data) {
      return 22 + name.encodingLength(data.mname) + name.encodingLength(data.rname);
    };
    var rtxt = exports.txt = {};
    rtxt.encode = function(data, buf, offset) {
      if (!Array.isArray(data)) data = [data];
      for (let i = 0; i < data.length; i++) {
        if (typeof data[i] === "string") {
          data[i] = Buffer2.from(data[i]);
        }
        if (!Buffer2.isBuffer(data[i])) {
          throw new Error("Must be a Buffer");
        }
      }
      if (!buf) buf = Buffer2.alloc(rtxt.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      data.forEach(function(d) {
        buf[offset++] = d.length;
        d.copy(buf, offset, 0, d.length);
        offset += d.length;
      });
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rtxt.encode.bytes = offset - oldOffset;
      return buf;
    };
    rtxt.encode.bytes = 0;
    rtxt.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      let remaining = buf.readUInt16BE(offset);
      offset += 2;
      let data = [];
      while (remaining > 0) {
        const len = buf[offset++];
        --remaining;
        if (remaining < len) {
          throw new Error("Buffer overflow");
        }
        data.push(buf.slice(offset, offset + len));
        offset += len;
        remaining -= len;
      }
      rtxt.decode.bytes = offset - oldOffset;
      return data;
    };
    rtxt.decode.bytes = 0;
    rtxt.encodingLength = function(data) {
      if (!Array.isArray(data)) data = [data];
      let length = 2;
      data.forEach(function(buf) {
        if (typeof buf === "string") {
          length += Buffer2.byteLength(buf) + 1;
        } else {
          length += buf.length + 1;
        }
      });
      return length;
    };
    var rnull = exports.null = {};
    rnull.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rnull.encodingLength(data));
      if (!offset) offset = 0;
      if (typeof data === "string") data = Buffer2.from(data);
      if (!data) data = Buffer2.alloc(0);
      const oldOffset = offset;
      offset += 2;
      const len = data.length;
      data.copy(buf, offset, 0, len);
      offset += len;
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rnull.encode.bytes = offset - oldOffset;
      return buf;
    };
    rnull.encode.bytes = 0;
    rnull.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const len = buf.readUInt16BE(offset);
      offset += 2;
      const data = buf.slice(offset, offset + len);
      offset += len;
      rnull.decode.bytes = offset - oldOffset;
      return data;
    };
    rnull.decode.bytes = 0;
    rnull.encodingLength = function(data) {
      if (!data) return 2;
      return (Buffer2.isBuffer(data) ? data.length : Buffer2.byteLength(data)) + 2;
    };
    var rhinfo = exports.hinfo = {};
    rhinfo.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rhinfo.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      string.encode(data.cpu, buf, offset);
      offset += string.encode.bytes;
      string.encode(data.os, buf, offset);
      offset += string.encode.bytes;
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rhinfo.encode.bytes = offset - oldOffset;
      return buf;
    };
    rhinfo.encode.bytes = 0;
    rhinfo.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.cpu = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.os = string.decode(buf, offset);
      offset += string.decode.bytes;
      rhinfo.decode.bytes = offset - oldOffset;
      return data;
    };
    rhinfo.decode.bytes = 0;
    rhinfo.encodingLength = function(data) {
      return string.encodingLength(data.cpu) + string.encodingLength(data.os) + 2;
    };
    var rptr = exports.ptr = {};
    var rcname = exports.cname = rptr;
    var rdname = exports.dname = rptr;
    rptr.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rptr.encodingLength(data));
      if (!offset) offset = 0;
      name.encode(data, buf, offset + 2);
      buf.writeUInt16BE(name.encode.bytes, offset);
      rptr.encode.bytes = name.encode.bytes + 2;
      return buf;
    };
    rptr.encode.bytes = 0;
    rptr.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const data = name.decode(buf, offset + 2);
      rptr.decode.bytes = name.decode.bytes + 2;
      return data;
    };
    rptr.decode.bytes = 0;
    rptr.encodingLength = function(data) {
      return name.encodingLength(data) + 2;
    };
    var rsrv = exports.srv = {};
    rsrv.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rsrv.encodingLength(data));
      if (!offset) offset = 0;
      buf.writeUInt16BE(data.priority || 0, offset + 2);
      buf.writeUInt16BE(data.weight || 0, offset + 4);
      buf.writeUInt16BE(data.port || 0, offset + 6);
      name.encode(data.target, buf, offset + 8);
      const len = name.encode.bytes + 6;
      buf.writeUInt16BE(len, offset);
      rsrv.encode.bytes = len + 2;
      return buf;
    };
    rsrv.encode.bytes = 0;
    rsrv.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf.readUInt16BE(offset);
      const data = {};
      data.priority = buf.readUInt16BE(offset + 2);
      data.weight = buf.readUInt16BE(offset + 4);
      data.port = buf.readUInt16BE(offset + 6);
      data.target = name.decode(buf, offset + 8);
      rsrv.decode.bytes = len + 2;
      return data;
    };
    rsrv.decode.bytes = 0;
    rsrv.encodingLength = function(data) {
      return 8 + name.encodingLength(data.target);
    };
    var rcaa = exports.caa = {};
    rcaa.ISSUER_CRITICAL = 1 << 7;
    rcaa.encode = function(data, buf, offset) {
      const len = rcaa.encodingLength(data);
      if (!buf) buf = Buffer2.alloc(rcaa.encodingLength(data));
      if (!offset) offset = 0;
      if (data.issuerCritical) {
        data.flags = rcaa.ISSUER_CRITICAL;
      }
      buf.writeUInt16BE(len - 2, offset);
      offset += 2;
      buf.writeUInt8(data.flags || 0, offset);
      offset += 1;
      string.encode(data.tag, buf, offset);
      offset += string.encode.bytes;
      buf.write(data.value, offset);
      offset += Buffer2.byteLength(data.value);
      rcaa.encode.bytes = len;
      return buf;
    };
    rcaa.encode.bytes = 0;
    rcaa.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf.readUInt16BE(offset);
      offset += 2;
      const oldOffset = offset;
      const data = {};
      data.flags = buf.readUInt8(offset);
      offset += 1;
      data.tag = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.value = buf.toString("utf-8", offset, oldOffset + len);
      data.issuerCritical = !!(data.flags & rcaa.ISSUER_CRITICAL);
      rcaa.decode.bytes = len + 2;
      return data;
    };
    rcaa.decode.bytes = 0;
    rcaa.encodingLength = function(data) {
      return string.encodingLength(data.tag) + string.encodingLength(data.value) + 2;
    };
    var rmx = exports.mx = {};
    rmx.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rmx.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      buf.writeUInt16BE(data.preference || 0, offset);
      offset += 2;
      name.encode(data.exchange, buf, offset);
      offset += name.encode.bytes;
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rmx.encode.bytes = offset - oldOffset;
      return buf;
    };
    rmx.encode.bytes = 0;
    rmx.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.preference = buf.readUInt16BE(offset);
      offset += 2;
      data.exchange = name.decode(buf, offset);
      offset += name.decode.bytes;
      rmx.decode.bytes = offset - oldOffset;
      return data;
    };
    rmx.encodingLength = function(data) {
      return 4 + name.encodingLength(data.exchange);
    };
    var ra = exports.a = {};
    ra.encode = function(host, buf, offset) {
      if (!buf) buf = Buffer2.alloc(ra.encodingLength(host));
      if (!offset) offset = 0;
      buf.writeUInt16BE(4, offset);
      offset += 2;
      ip.v4.encode(host, buf, offset);
      ra.encode.bytes = 6;
      return buf;
    };
    ra.encode.bytes = 0;
    ra.decode = function(buf, offset) {
      if (!offset) offset = 0;
      offset += 2;
      const host = ip.v4.decode(buf, offset);
      ra.decode.bytes = 6;
      return host;
    };
    ra.decode.bytes = 0;
    ra.encodingLength = function() {
      return 6;
    };
    var raaaa = exports.aaaa = {};
    raaaa.encode = function(host, buf, offset) {
      if (!buf) buf = Buffer2.alloc(raaaa.encodingLength(host));
      if (!offset) offset = 0;
      buf.writeUInt16BE(16, offset);
      offset += 2;
      ip.v6.encode(host, buf, offset);
      raaaa.encode.bytes = 18;
      return buf;
    };
    raaaa.encode.bytes = 0;
    raaaa.decode = function(buf, offset) {
      if (!offset) offset = 0;
      offset += 2;
      const host = ip.v6.decode(buf, offset);
      raaaa.decode.bytes = 18;
      return host;
    };
    raaaa.decode.bytes = 0;
    raaaa.encodingLength = function() {
      return 18;
    };
    var roption = exports.option = {};
    roption.encode = function(option, buf, offset) {
      if (!buf) buf = Buffer2.alloc(roption.encodingLength(option));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const code = optioncodes.toCode(option.code);
      buf.writeUInt16BE(code, offset);
      offset += 2;
      if (option.data) {
        buf.writeUInt16BE(option.data.length, offset);
        offset += 2;
        option.data.copy(buf, offset);
        offset += option.data.length;
      } else {
        switch (code) {
          // case 3: NSID.  No encode makes sense.
          // case 5,6,7: Not implementable
          case 8:
            const spl = option.sourcePrefixLength || 0;
            const fam = option.family || ip.familyOf(option.ip);
            const ipBuf = ip.encode(option.ip, Buffer2.alloc);
            const ipLen = Math.ceil(spl / 8);
            buf.writeUInt16BE(ipLen + 4, offset);
            offset += 2;
            buf.writeUInt16BE(fam, offset);
            offset += 2;
            buf.writeUInt8(spl, offset++);
            buf.writeUInt8(option.scopePrefixLength || 0, offset++);
            ipBuf.copy(buf, offset, 0, ipLen);
            offset += ipLen;
            break;
          // case 9: EXPIRE (experimental)
          // case 10: COOKIE.  No encode makes sense.
          case 11:
            if (option.timeout) {
              buf.writeUInt16BE(2, offset);
              offset += 2;
              buf.writeUInt16BE(option.timeout, offset);
              offset += 2;
            } else {
              buf.writeUInt16BE(0, offset);
              offset += 2;
            }
            break;
          case 12:
            const len = option.length || 0;
            buf.writeUInt16BE(len, offset);
            offset += 2;
            buf.fill(0, offset, offset + len);
            offset += len;
            break;
          // case 13:  CHAIN.  Experimental.
          case 14:
            const tagsLen = option.tags.length * 2;
            buf.writeUInt16BE(tagsLen, offset);
            offset += 2;
            for (const tag of option.tags) {
              buf.writeUInt16BE(tag, offset);
              offset += 2;
            }
            break;
          default:
            throw new Error(`Unknown roption code: ${option.code}`);
        }
      }
      roption.encode.bytes = offset - oldOffset;
      return buf;
    };
    roption.encode.bytes = 0;
    roption.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const option = {};
      option.code = buf.readUInt16BE(offset);
      option.type = optioncodes.toString(option.code);
      offset += 2;
      const len = buf.readUInt16BE(offset);
      offset += 2;
      option.data = buf.slice(offset, offset + len);
      switch (option.code) {
        // case 3: NSID.  No decode makes sense.
        case 8:
          option.family = buf.readUInt16BE(offset);
          offset += 2;
          option.sourcePrefixLength = buf.readUInt8(offset++);
          option.scopePrefixLength = buf.readUInt8(offset++);
          const padded = Buffer2.alloc(option.family === 1 ? 4 : 16);
          buf.copy(padded, 0, offset, offset + len - 4);
          option.ip = ip.decode(padded);
          break;
        // case 12: Padding.  No decode makes sense.
        case 11:
          if (len > 0) {
            option.timeout = buf.readUInt16BE(offset);
            offset += 2;
          }
          break;
        case 14:
          option.tags = [];
          for (let i = 0; i < len; i += 2) {
            option.tags.push(buf.readUInt16BE(offset));
            offset += 2;
          }
      }
      roption.decode.bytes = len + 4;
      return option;
    };
    roption.decode.bytes = 0;
    roption.encodingLength = function(option) {
      if (option.data) {
        return option.data.length + 4;
      }
      const code = optioncodes.toCode(option.code);
      switch (code) {
        case 8:
          const spl = option.sourcePrefixLength || 0;
          return Math.ceil(spl / 8) + 8;
        case 11:
          return typeof option.timeout === "number" ? 6 : 4;
        case 12:
          return option.length + 4;
        case 14:
          return 4 + option.tags.length * 2;
      }
      throw new Error(`Unknown roption code: ${option.code}`);
    };
    var ropt = exports.opt = {};
    ropt.encode = function(options2, buf, offset) {
      if (!buf) buf = Buffer2.alloc(ropt.encodingLength(options2));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const rdlen = encodingLengthList(options2, roption);
      buf.writeUInt16BE(rdlen, offset);
      offset = encodeList(options2, roption, buf, offset + 2);
      ropt.encode.bytes = offset - oldOffset;
      return buf;
    };
    ropt.encode.bytes = 0;
    ropt.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const options2 = [];
      let rdlen = buf.readUInt16BE(offset);
      offset += 2;
      let o = 0;
      while (rdlen > 0) {
        options2[o++] = roption.decode(buf, offset);
        offset += roption.decode.bytes;
        rdlen -= roption.decode.bytes;
      }
      ropt.decode.bytes = offset - oldOffset;
      return options2;
    };
    ropt.decode.bytes = 0;
    ropt.encodingLength = function(options2) {
      return 2 + encodingLengthList(options2 || [], roption);
    };
    var rdnskey = exports.dnskey = {};
    rdnskey.PROTOCOL_DNSSEC = 3;
    rdnskey.ZONE_KEY = 128;
    rdnskey.SECURE_ENTRYPOINT = 32768;
    rdnskey.encode = function(key, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rdnskey.encodingLength(key));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const keydata = key.key;
      if (!Buffer2.isBuffer(keydata)) {
        throw new Error("Key must be a Buffer");
      }
      offset += 2;
      buf.writeUInt16BE(key.flags, offset);
      offset += 2;
      buf.writeUInt8(rdnskey.PROTOCOL_DNSSEC, offset);
      offset += 1;
      buf.writeUInt8(key.algorithm, offset);
      offset += 1;
      keydata.copy(buf, offset, 0, keydata.length);
      offset += keydata.length;
      rdnskey.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rdnskey.encode.bytes - 2, oldOffset);
      return buf;
    };
    rdnskey.encode.bytes = 0;
    rdnskey.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var key = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      key.flags = buf.readUInt16BE(offset);
      offset += 2;
      if (buf.readUInt8(offset) !== rdnskey.PROTOCOL_DNSSEC) {
        throw new Error("Protocol must be 3");
      }
      offset += 1;
      key.algorithm = buf.readUInt8(offset);
      offset += 1;
      key.key = buf.slice(offset, oldOffset + length + 2);
      offset += key.key.length;
      rdnskey.decode.bytes = offset - oldOffset;
      return key;
    };
    rdnskey.decode.bytes = 0;
    rdnskey.encodingLength = function(key) {
      return 6 + Buffer2.byteLength(key.key);
    };
    var rrrsig = exports.rrsig = {};
    rrrsig.encode = function(sig, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rrrsig.encodingLength(sig));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const signature = sig.signature;
      if (!Buffer2.isBuffer(signature)) {
        throw new Error("Signature must be a Buffer");
      }
      offset += 2;
      buf.writeUInt16BE(types.toType(sig.typeCovered), offset);
      offset += 2;
      buf.writeUInt8(sig.algorithm, offset);
      offset += 1;
      buf.writeUInt8(sig.labels, offset);
      offset += 1;
      buf.writeUInt32BE(sig.originalTTL, offset);
      offset += 4;
      buf.writeUInt32BE(sig.expiration, offset);
      offset += 4;
      buf.writeUInt32BE(sig.inception, offset);
      offset += 4;
      buf.writeUInt16BE(sig.keyTag, offset);
      offset += 2;
      name.encode(sig.signersName, buf, offset);
      offset += name.encode.bytes;
      signature.copy(buf, offset, 0, signature.length);
      offset += signature.length;
      rrrsig.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rrrsig.encode.bytes - 2, oldOffset);
      return buf;
    };
    rrrsig.encode.bytes = 0;
    rrrsig.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var sig = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      sig.typeCovered = types.toString(buf.readUInt16BE(offset));
      offset += 2;
      sig.algorithm = buf.readUInt8(offset);
      offset += 1;
      sig.labels = buf.readUInt8(offset);
      offset += 1;
      sig.originalTTL = buf.readUInt32BE(offset);
      offset += 4;
      sig.expiration = buf.readUInt32BE(offset);
      offset += 4;
      sig.inception = buf.readUInt32BE(offset);
      offset += 4;
      sig.keyTag = buf.readUInt16BE(offset);
      offset += 2;
      sig.signersName = name.decode(buf, offset);
      offset += name.decode.bytes;
      sig.signature = buf.slice(offset, oldOffset + length + 2);
      offset += sig.signature.length;
      rrrsig.decode.bytes = offset - oldOffset;
      return sig;
    };
    rrrsig.decode.bytes = 0;
    rrrsig.encodingLength = function(sig) {
      return 20 + name.encodingLength(sig.signersName) + Buffer2.byteLength(sig.signature);
    };
    var rrp = exports.rp = {};
    rrp.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rrp.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      name.encode(data.mbox || ".", buf, offset, { mail: true });
      offset += name.encode.bytes;
      name.encode(data.txt || ".", buf, offset);
      offset += name.encode.bytes;
      rrp.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rrp.encode.bytes - 2, oldOffset);
      return buf;
    };
    rrp.encode.bytes = 0;
    rrp.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.mbox = name.decode(buf, offset, { mail: true }) || ".";
      offset += name.decode.bytes;
      data.txt = name.decode(buf, offset) || ".";
      offset += name.decode.bytes;
      rrp.decode.bytes = offset - oldOffset;
      return data;
    };
    rrp.decode.bytes = 0;
    rrp.encodingLength = function(data) {
      return 2 + name.encodingLength(data.mbox || ".") + name.encodingLength(data.txt || ".");
    };
    var typebitmap = {};
    typebitmap.encode = function(typelist, buf, offset) {
      if (!buf) buf = Buffer2.alloc(typebitmap.encodingLength(typelist));
      if (!offset) offset = 0;
      const oldOffset = offset;
      var typesByWindow = [];
      for (var i = 0; i < typelist.length; i++) {
        var typeid = types.toType(typelist[i]);
        if (typesByWindow[typeid >> 8] === void 0) {
          typesByWindow[typeid >> 8] = [];
        }
        typesByWindow[typeid >> 8][typeid >> 3 & 31] |= 1 << 7 - (typeid & 7);
      }
      for (i = 0; i < typesByWindow.length; i++) {
        if (typesByWindow[i] !== void 0) {
          var windowBuf = Buffer2.from(typesByWindow[i]);
          buf.writeUInt8(i, offset);
          offset += 1;
          buf.writeUInt8(windowBuf.length, offset);
          offset += 1;
          windowBuf.copy(buf, offset);
          offset += windowBuf.length;
        }
      }
      typebitmap.encode.bytes = offset - oldOffset;
      return buf;
    };
    typebitmap.encode.bytes = 0;
    typebitmap.decode = function(buf, offset, length) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var typelist = [];
      while (offset - oldOffset < length) {
        var window = buf.readUInt8(offset);
        offset += 1;
        var windowLength = buf.readUInt8(offset);
        offset += 1;
        for (var i = 0; i < windowLength; i++) {
          var b = buf.readUInt8(offset + i);
          for (var j = 0; j < 8; j++) {
            if (b & 1 << 7 - j) {
              var typeid = types.toString(window << 8 | i << 3 | j);
              typelist.push(typeid);
            }
          }
        }
        offset += windowLength;
      }
      typebitmap.decode.bytes = offset - oldOffset;
      return typelist;
    };
    typebitmap.decode.bytes = 0;
    typebitmap.encodingLength = function(typelist) {
      var extents = [];
      for (var i = 0; i < typelist.length; i++) {
        var typeid = types.toType(typelist[i]);
        extents[typeid >> 8] = Math.max(extents[typeid >> 8] || 0, typeid & 255);
      }
      var len = 0;
      for (i = 0; i < extents.length; i++) {
        if (extents[i] !== void 0) {
          len += 2 + Math.ceil((extents[i] + 1) / 8);
        }
      }
      return len;
    };
    var rnsec = exports.nsec = {};
    rnsec.encode = function(record3, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rnsec.encodingLength(record3));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      name.encode(record3.nextDomain, buf, offset);
      offset += name.encode.bytes;
      typebitmap.encode(record3.rrtypes, buf, offset);
      offset += typebitmap.encode.bytes;
      rnsec.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rnsec.encode.bytes - 2, oldOffset);
      return buf;
    };
    rnsec.encode.bytes = 0;
    rnsec.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var record3 = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      record3.nextDomain = name.decode(buf, offset);
      offset += name.decode.bytes;
      record3.rrtypes = typebitmap.decode(buf, offset, length - (offset - oldOffset));
      offset += typebitmap.decode.bytes;
      rnsec.decode.bytes = offset - oldOffset;
      return record3;
    };
    rnsec.decode.bytes = 0;
    rnsec.encodingLength = function(record3) {
      return 2 + name.encodingLength(record3.nextDomain) + typebitmap.encodingLength(record3.rrtypes);
    };
    var rnsec3 = exports.nsec3 = {};
    rnsec3.encode = function(record3, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rnsec3.encodingLength(record3));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const salt = record3.salt;
      if (!Buffer2.isBuffer(salt)) {
        throw new Error("salt must be a Buffer");
      }
      const nextDomain = record3.nextDomain;
      if (!Buffer2.isBuffer(nextDomain)) {
        throw new Error("nextDomain must be a Buffer");
      }
      offset += 2;
      buf.writeUInt8(record3.algorithm, offset);
      offset += 1;
      buf.writeUInt8(record3.flags, offset);
      offset += 1;
      buf.writeUInt16BE(record3.iterations, offset);
      offset += 2;
      buf.writeUInt8(salt.length, offset);
      offset += 1;
      salt.copy(buf, offset, 0, salt.length);
      offset += salt.length;
      buf.writeUInt8(nextDomain.length, offset);
      offset += 1;
      nextDomain.copy(buf, offset, 0, nextDomain.length);
      offset += nextDomain.length;
      typebitmap.encode(record3.rrtypes, buf, offset);
      offset += typebitmap.encode.bytes;
      rnsec3.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rnsec3.encode.bytes - 2, oldOffset);
      return buf;
    };
    rnsec3.encode.bytes = 0;
    rnsec3.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var record3 = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      record3.algorithm = buf.readUInt8(offset);
      offset += 1;
      record3.flags = buf.readUInt8(offset);
      offset += 1;
      record3.iterations = buf.readUInt16BE(offset);
      offset += 2;
      const saltLength = buf.readUInt8(offset);
      offset += 1;
      record3.salt = buf.slice(offset, offset + saltLength);
      offset += saltLength;
      const hashLength = buf.readUInt8(offset);
      offset += 1;
      record3.nextDomain = buf.slice(offset, offset + hashLength);
      offset += hashLength;
      record3.rrtypes = typebitmap.decode(buf, offset, length - (offset - oldOffset));
      offset += typebitmap.decode.bytes;
      rnsec3.decode.bytes = offset - oldOffset;
      return record3;
    };
    rnsec3.decode.bytes = 0;
    rnsec3.encodingLength = function(record3) {
      return 8 + record3.salt.length + record3.nextDomain.length + typebitmap.encodingLength(record3.rrtypes);
    };
    var rds = exports.ds = {};
    rds.encode = function(digest, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rds.encodingLength(digest));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const digestdata = digest.digest;
      if (!Buffer2.isBuffer(digestdata)) {
        throw new Error("Digest must be a Buffer");
      }
      offset += 2;
      buf.writeUInt16BE(digest.keyTag, offset);
      offset += 2;
      buf.writeUInt8(digest.algorithm, offset);
      offset += 1;
      buf.writeUInt8(digest.digestType, offset);
      offset += 1;
      digestdata.copy(buf, offset, 0, digestdata.length);
      offset += digestdata.length;
      rds.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rds.encode.bytes - 2, oldOffset);
      return buf;
    };
    rds.encode.bytes = 0;
    rds.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var digest = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      digest.keyTag = buf.readUInt16BE(offset);
      offset += 2;
      digest.algorithm = buf.readUInt8(offset);
      offset += 1;
      digest.digestType = buf.readUInt8(offset);
      offset += 1;
      digest.digest = buf.slice(offset, oldOffset + length + 2);
      offset += digest.digest.length;
      rds.decode.bytes = offset - oldOffset;
      return digest;
    };
    rds.decode.bytes = 0;
    rds.encodingLength = function(digest) {
      return 6 + Buffer2.byteLength(digest.digest);
    };
    var rsshfp = exports.sshfp = {};
    rsshfp.getFingerprintLengthForHashType = function getFingerprintLengthForHashType(hashType) {
      switch (hashType) {
        case 1:
          return 20;
        case 2:
          return 32;
      }
    };
    rsshfp.encode = function encode(record3, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rsshfp.encodingLength(record3));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      buf[offset] = record3.algorithm;
      offset += 1;
      buf[offset] = record3.hash;
      offset += 1;
      const fingerprintBuf = Buffer2.from(record3.fingerprint.toUpperCase(), "hex");
      if (fingerprintBuf.length !== rsshfp.getFingerprintLengthForHashType(record3.hash)) {
        throw new Error("Invalid fingerprint length");
      }
      fingerprintBuf.copy(buf, offset);
      offset += fingerprintBuf.byteLength;
      rsshfp.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rsshfp.encode.bytes - 2, oldOffset);
      return buf;
    };
    rsshfp.encode.bytes = 0;
    rsshfp.decode = function decode(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const record3 = {};
      offset += 2;
      record3.algorithm = buf[offset];
      offset += 1;
      record3.hash = buf[offset];
      offset += 1;
      const fingerprintLength = rsshfp.getFingerprintLengthForHashType(record3.hash);
      record3.fingerprint = buf.slice(offset, offset + fingerprintLength).toString("hex").toUpperCase();
      offset += fingerprintLength;
      rsshfp.decode.bytes = offset - oldOffset;
      return record3;
    };
    rsshfp.decode.bytes = 0;
    rsshfp.encodingLength = function(record3) {
      return 4 + Buffer2.from(record3.fingerprint, "hex").byteLength;
    };
    var rnaptr = exports.naptr = {};
    rnaptr.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rnaptr.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      buf.writeUInt16BE(data.order || 0, offset);
      offset += 2;
      buf.writeUInt16BE(data.preference || 0, offset);
      offset += 2;
      string.encode(data.flags, buf, offset);
      offset += string.encode.bytes;
      string.encode(data.services, buf, offset);
      offset += string.encode.bytes;
      string.encode(data.regexp, buf, offset);
      offset += string.encode.bytes;
      name.encode(data.replacement, buf, offset);
      offset += name.encode.bytes;
      rnaptr.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rnaptr.encode.bytes - 2, oldOffset);
      return buf;
    };
    rnaptr.encode.bytes = 0;
    rnaptr.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.order = buf.readUInt16BE(offset);
      offset += 2;
      data.preference = buf.readUInt16BE(offset);
      offset += 2;
      data.flags = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.services = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.regexp = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.replacement = name.decode(buf, offset);
      offset += name.decode.bytes;
      rnaptr.decode.bytes = offset - oldOffset;
      return data;
    };
    rnaptr.decode.bytes = 0;
    rnaptr.encodingLength = function(data) {
      return string.encodingLength(data.flags) + string.encodingLength(data.services) + string.encodingLength(data.regexp) + name.encodingLength(data.replacement) + 6;
    };
    var rtlsa = exports.tlsa = {};
    rtlsa.encode = function(cert, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rtlsa.encodingLength(cert));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const certdata = cert.certificate;
      if (!Buffer2.isBuffer(certdata)) {
        throw new Error("Certificate must be a Buffer");
      }
      offset += 2;
      buf.writeUInt8(cert.usage, offset);
      offset += 1;
      buf.writeUInt8(cert.selector, offset);
      offset += 1;
      buf.writeUInt8(cert.matchingType, offset);
      offset += 1;
      certdata.copy(buf, offset, 0, certdata.length);
      offset += certdata.length;
      rtlsa.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rtlsa.encode.bytes - 2, oldOffset);
      return buf;
    };
    rtlsa.encode.bytes = 0;
    rtlsa.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const cert = {};
      const length = buf.readUInt16BE(offset);
      offset += 2;
      cert.usage = buf.readUInt8(offset);
      offset += 1;
      cert.selector = buf.readUInt8(offset);
      offset += 1;
      cert.matchingType = buf.readUInt8(offset);
      offset += 1;
      cert.certificate = buf.slice(offset, oldOffset + length + 2);
      offset += cert.certificate.length;
      rtlsa.decode.bytes = offset - oldOffset;
      return cert;
    };
    rtlsa.decode.bytes = 0;
    rtlsa.encodingLength = function(cert) {
      return 5 + Buffer2.byteLength(cert.certificate);
    };
    var renc = exports.record = function(type) {
      switch (type.toUpperCase()) {
        case "A":
          return ra;
        case "PTR":
          return rptr;
        case "CNAME":
          return rcname;
        case "DNAME":
          return rdname;
        case "TXT":
          return rtxt;
        case "NULL":
          return rnull;
        case "AAAA":
          return raaaa;
        case "SRV":
          return rsrv;
        case "HINFO":
          return rhinfo;
        case "CAA":
          return rcaa;
        case "NS":
          return rns;
        case "SOA":
          return rsoa;
        case "MX":
          return rmx;
        case "OPT":
          return ropt;
        case "DNSKEY":
          return rdnskey;
        case "RRSIG":
          return rrrsig;
        case "RP":
          return rrp;
        case "NSEC":
          return rnsec;
        case "NSEC3":
          return rnsec3;
        case "SSHFP":
          return rsshfp;
        case "DS":
          return rds;
        case "NAPTR":
          return rnaptr;
        case "TLSA":
          return rtlsa;
      }
      return runknown;
    };
    var answer = exports.answer = {};
    answer.encode = function(a, buf, offset) {
      if (!buf) buf = Buffer2.alloc(answer.encodingLength(a));
      if (!offset) offset = 0;
      const oldOffset = offset;
      name.encode(a.name, buf, offset);
      offset += name.encode.bytes;
      buf.writeUInt16BE(types.toType(a.type), offset);
      if (a.type.toUpperCase() === "OPT") {
        if (a.name !== ".") {
          throw new Error("OPT name must be root.");
        }
        buf.writeUInt16BE(a.udpPayloadSize || 4096, offset + 2);
        buf.writeUInt8(a.extendedRcode || 0, offset + 4);
        buf.writeUInt8(a.ednsVersion || 0, offset + 5);
        buf.writeUInt16BE(a.flags || 0, offset + 6);
        offset += 8;
        ropt.encode(a.options || [], buf, offset);
        offset += ropt.encode.bytes;
      } else {
        let klass = classes.toClass(a.class === void 0 ? "IN" : a.class);
        if (a.flush) klass |= FLUSH_MASK;
        buf.writeUInt16BE(klass, offset + 2);
        buf.writeUInt32BE(a.ttl || 0, offset + 4);
        offset += 8;
        const enc = renc(a.type);
        enc.encode(a.data, buf, offset);
        offset += enc.encode.bytes;
      }
      answer.encode.bytes = offset - oldOffset;
      return buf;
    };
    answer.encode.bytes = 0;
    answer.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const a = {};
      const oldOffset = offset;
      a.name = name.decode(buf, offset);
      offset += name.decode.bytes;
      a.type = types.toString(buf.readUInt16BE(offset));
      if (a.type === "OPT") {
        a.udpPayloadSize = buf.readUInt16BE(offset + 2);
        a.extendedRcode = buf.readUInt8(offset + 4);
        a.ednsVersion = buf.readUInt8(offset + 5);
        a.flags = buf.readUInt16BE(offset + 6);
        a.flag_do = (a.flags >> 15 & 1) === 1;
        a.options = ropt.decode(buf, offset + 8);
        offset += 8 + ropt.decode.bytes;
      } else {
        const klass = buf.readUInt16BE(offset + 2);
        a.ttl = buf.readUInt32BE(offset + 4);
        a.class = classes.toString(klass & NOT_FLUSH_MASK);
        a.flush = !!(klass & FLUSH_MASK);
        const enc = renc(a.type);
        a.data = enc.decode(buf, offset + 8);
        offset += 8 + enc.decode.bytes;
      }
      answer.decode.bytes = offset - oldOffset;
      return a;
    };
    answer.decode.bytes = 0;
    answer.encodingLength = function(a) {
      const data = a.data !== null && a.data !== void 0 ? a.data : a.options;
      return name.encodingLength(a.name) + 8 + renc(a.type).encodingLength(data);
    };
    var question = exports.question = {};
    question.encode = function(q, buf, offset) {
      if (!buf) buf = Buffer2.alloc(question.encodingLength(q));
      if (!offset) offset = 0;
      const oldOffset = offset;
      name.encode(q.name, buf, offset);
      offset += name.encode.bytes;
      buf.writeUInt16BE(types.toType(q.type), offset);
      offset += 2;
      buf.writeUInt16BE(classes.toClass(q.class === void 0 ? "IN" : q.class), offset);
      offset += 2;
      question.encode.bytes = offset - oldOffset;
      return q;
    };
    question.encode.bytes = 0;
    question.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const q = {};
      q.name = name.decode(buf, offset);
      offset += name.decode.bytes;
      q.type = types.toString(buf.readUInt16BE(offset));
      offset += 2;
      q.class = classes.toString(buf.readUInt16BE(offset));
      offset += 2;
      const qu = !!(q.class & QU_MASK);
      if (qu) q.class &= NOT_QU_MASK;
      question.decode.bytes = offset - oldOffset;
      return q;
    };
    question.decode.bytes = 0;
    question.encodingLength = function(q) {
      return name.encodingLength(q.name) + 4;
    };
    exports.AUTHORITATIVE_ANSWER = 1 << 10;
    exports.TRUNCATED_RESPONSE = 1 << 9;
    exports.RECURSION_DESIRED = 1 << 8;
    exports.RECURSION_AVAILABLE = 1 << 7;
    exports.AUTHENTIC_DATA = 1 << 5;
    exports.CHECKING_DISABLED = 1 << 4;
    exports.DNSSEC_OK = 1 << 15;
    exports.encode = function(result, buf, offset) {
      const allocing = !buf;
      if (allocing) buf = Buffer2.alloc(exports.encodingLength(result));
      if (!offset) offset = 0;
      const oldOffset = offset;
      if (!result.questions) result.questions = [];
      if (!result.answers) result.answers = [];
      if (!result.authorities) result.authorities = [];
      if (!result.additionals) result.additionals = [];
      header.encode(result, buf, offset);
      offset += header.encode.bytes;
      offset = encodeList(result.questions, question, buf, offset);
      offset = encodeList(result.answers, answer, buf, offset);
      offset = encodeList(result.authorities, answer, buf, offset);
      offset = encodeList(result.additionals, answer, buf, offset);
      exports.encode.bytes = offset - oldOffset;
      if (allocing && exports.encode.bytes !== buf.length) {
        return buf.slice(0, exports.encode.bytes);
      }
      return buf;
    };
    exports.encode.bytes = 0;
    exports.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const result = header.decode(buf, offset);
      offset += header.decode.bytes;
      offset = decodeList(result.questions, question, buf, offset);
      offset = decodeList(result.answers, answer, buf, offset);
      offset = decodeList(result.authorities, answer, buf, offset);
      offset = decodeList(result.additionals, answer, buf, offset);
      exports.decode.bytes = offset - oldOffset;
      return result;
    };
    exports.decode.bytes = 0;
    exports.encodingLength = function(result) {
      return header.encodingLength(result) + encodingLengthList(result.questions || [], question) + encodingLengthList(result.answers || [], answer) + encodingLengthList(result.authorities || [], answer) + encodingLengthList(result.additionals || [], answer);
    };
    exports.streamEncode = function(result) {
      const buf = exports.encode(result);
      const sbuf = Buffer2.alloc(2);
      sbuf.writeUInt16BE(buf.byteLength);
      const combine = Buffer2.concat([sbuf, buf]);
      exports.streamEncode.bytes = combine.byteLength;
      return combine;
    };
    exports.streamEncode.bytes = 0;
    exports.streamDecode = function(sbuf) {
      const len = sbuf.readUInt16BE(0);
      if (sbuf.byteLength < len + 2) {
        return null;
      }
      const result = exports.decode(sbuf.slice(2));
      exports.streamDecode.bytes = exports.decode.bytes;
      return result;
    };
    exports.streamDecode.bytes = 0;
    function encodingLengthList(list, enc) {
      let len = 0;
      for (let i = 0; i < list.length; i++) len += enc.encodingLength(list[i]);
      return len;
    }
    function encodeList(list, enc, buf, offset) {
      for (let i = 0; i < list.length; i++) {
        enc.encode(list[i], buf, offset);
        offset += enc.encode.bytes;
      }
      return offset;
    }
    function decodeList(list, enc, buf, offset) {
      for (let i = 0; i < list.length; i++) {
        list[i] = enc.decode(buf, offset);
        offset += enc.decode.bytes;
      }
      return offset;
    }
  }
});

// node_modules/thunky/index.js
var require_thunky = __commonJS({
  "node_modules/thunky/index.js"(exports, module) {
    "use strict";
    var nextTick = nextTickArgs;
    process.nextTick(upgrade, 42);
    module.exports = thunky;
    function thunky(fn) {
      var state = run;
      return thunk;
      function thunk(callback) {
        state(callback || noop);
      }
      function run(callback) {
        var stack = [callback];
        state = wait;
        fn(done);
        function wait(callback2) {
          stack.push(callback2);
        }
        function done(err) {
          var args = arguments;
          state = isError(err) ? run : finished;
          while (stack.length) finished(stack.shift());
          function finished(callback2) {
            nextTick(apply, callback2, args);
          }
        }
      }
    }
    function isError(err) {
      return Object.prototype.toString.call(err) === "[object Error]";
    }
    function noop() {
    }
    function apply(callback, args) {
      callback.apply(null, args);
    }
    function upgrade(val) {
      if (val === 42) nextTick = process.nextTick;
    }
    function nextTickArgs(fn, a, b) {
      process.nextTick(function() {
        fn(a, b);
      });
    }
  }
});

// node_modules/multicast-dns/index.js
var require_multicast_dns = __commonJS({
  "node_modules/multicast-dns/index.js"(exports, module) {
    var packet = require_dns_packet();
    var dgram = __require("dgram");
    var thunky = require_thunky();
    var events = __require("events");
    var os = __require("os");
    var noop = function() {
    };
    module.exports = function(opts) {
      if (!opts) opts = {};
      var that = new events.EventEmitter();
      var port = typeof opts.port === "number" ? opts.port : 5353;
      var type = opts.type || "udp4";
      var ip = opts.ip || opts.host || (type === "udp4" ? "224.0.0.251" : null);
      var me = { address: ip, port };
      var memberships = {};
      var destroyed = false;
      var interval = null;
      if (type === "udp6" && (!ip || !opts.interface)) {
        throw new Error("For IPv6 multicast you must specify `ip` and `interface`");
      }
      var socket = opts.socket || dgram.createSocket({
        type,
        reuseAddr: opts.reuseAddr !== false,
        toString: function() {
          return type;
        }
      });
      socket.on("error", function(err) {
        if (err.code === "EACCES" || err.code === "EADDRINUSE") that.emit("error", err);
        else that.emit("warning", err);
      });
      socket.on("message", function(message, rinfo) {
        try {
          message = packet.decode(message);
        } catch (err) {
          that.emit("warning", err);
          return;
        }
        that.emit("packet", message, rinfo);
        if (message.type === "query") that.emit("query", message, rinfo);
        if (message.type === "response") that.emit("response", message, rinfo);
      });
      socket.on("listening", function() {
        if (!port) port = me.port = socket.address().port;
        if (opts.multicast !== false) {
          that.update();
          interval = setInterval(that.update, 5e3);
          socket.setMulticastTTL(opts.ttl || 255);
          socket.setMulticastLoopback(opts.loopback !== false);
        }
      });
      var bind = thunky(function(cb) {
        if (!port || opts.bind === false) return cb(null);
        socket.once("error", cb);
        socket.bind(port, opts.bind || opts.interface, function() {
          socket.removeListener("error", cb);
          cb(null);
        });
      });
      bind(function(err) {
        if (err) return that.emit("error", err);
        that.emit("ready");
      });
      that.send = function(value, rinfo, cb) {
        if (typeof rinfo === "function") return that.send(value, null, rinfo);
        if (!cb) cb = noop;
        if (!rinfo) rinfo = me;
        else if (!rinfo.host && !rinfo.address) rinfo.address = me.address;
        bind(onbind);
        function onbind(err) {
          if (destroyed) return cb();
          if (err) return cb(err);
          var message = packet.encode(value);
          socket.send(message, 0, message.length, rinfo.port, rinfo.address || rinfo.host, cb);
        }
      };
      that.response = that.respond = function(res, rinfo, cb) {
        if (Array.isArray(res)) res = { answers: res };
        res.type = "response";
        res.flags = (res.flags || 0) | packet.AUTHORITATIVE_ANSWER;
        that.send(res, rinfo, cb);
      };
      that.query = function(q, type2, rinfo, cb) {
        if (typeof type2 === "function") return that.query(q, null, null, type2);
        if (typeof type2 === "object" && type2 && type2.port) return that.query(q, null, type2, rinfo);
        if (typeof rinfo === "function") return that.query(q, type2, null, rinfo);
        if (!cb) cb = noop;
        if (typeof q === "string") q = [{ name: q, type: type2 || "ANY" }];
        if (Array.isArray(q)) q = { type: "query", questions: q };
        q.type = "query";
        that.send(q, rinfo, cb);
      };
      that.destroy = function(cb) {
        if (!cb) cb = noop;
        if (destroyed) return process.nextTick(cb);
        destroyed = true;
        clearInterval(interval);
        for (var iface in memberships) {
          try {
            socket.dropMembership(ip, iface);
          } catch (e) {
          }
        }
        memberships = {};
        socket.close(cb);
      };
      that.update = function() {
        var ifaces = opts.interface ? [].concat(opts.interface) : allInterfaces();
        var updated = false;
        for (var i = 0; i < ifaces.length; i++) {
          var addr = ifaces[i];
          if (memberships[addr]) continue;
          try {
            socket.addMembership(ip, addr);
            memberships[addr] = true;
            updated = true;
          } catch (err) {
            that.emit("warning", err);
          }
        }
        if (updated) {
          if (socket.setMulticastInterface) {
            try {
              socket.setMulticastInterface(opts.interface || defaultInterface());
            } catch (err) {
              that.emit("warning", err);
            }
          }
          that.emit("networkInterface");
        }
      };
      return that;
    };
    function defaultInterface() {
      var networks = os.networkInterfaces();
      var names = Object.keys(networks);
      for (var i = 0; i < names.length; i++) {
        var net = networks[names[i]];
        for (var j = 0; j < net.length; j++) {
          var iface = net[j];
          if (isIPv4(iface.family) && !iface.internal) {
            if (os.platform() === "darwin" && names[i] === "en0") return iface.address;
            return "0.0.0.0";
          }
        }
      }
      return "127.0.0.1";
    }
    function allInterfaces() {
      var networks = os.networkInterfaces();
      var names = Object.keys(networks);
      var res = [];
      for (var i = 0; i < names.length; i++) {
        var net = networks[names[i]];
        for (var j = 0; j < net.length; j++) {
          var iface = net[j];
          if (isIPv4(iface.family)) {
            res.push(iface.address);
            break;
          }
        }
      }
      return res;
    }
    function isIPv4(family) {
      return family === 4 || family === "IPv4";
    }
  }
});

// src/cli.js
import { parseArgs } from "node:util";
import { readFile, writeFile } from "node:fs/promises";
import { realpathSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { createInterface as createInterface2 } from "node:readline/promises";
import { Writable } from "node:stream";

// node_modules/ansi-regex/index.js
function ansiRegex({ onlyFirst = false } = {}) {
  const ST = "(?:\\u0007|\\u001B\\u005C|\\u009C)";
  const osc = `(?:(?:\\u001B\\]|\\u009D)[^\\u0007\\u001B\\u009C\\u009D]*${ST})`;
  const csi = "[\\u001B\\u009B][[\\]()#;?]*(?:\\d{1,4}(?:[;:]\\d{0,4})*)?[\\dA-PR-TZcf-nq-uy=><~]";
  const pattern = `${osc}|${csi}`;
  return new RegExp(pattern, onlyFirst ? void 0 : "g");
}

// node_modules/strip-ansi/index.js
var regex = ansiRegex();
function stripAnsi(string) {
  if (typeof string !== "string") {
    throw new TypeError(`Expected a \`string\`, got \`${typeof string}\``);
  }
  if (!string.includes("\x1B") && !string.includes("\x9B")) {
    return string;
  }
  return string.replace(regex, "");
}

// node_modules/get-east-asian-width/lookup-data.js
var ambiguousMinimalCodePoint = 161;
var ambiguousMaximumCodePoint = 1114109;
var ambiguousRanges = [161, 161, 164, 164, 167, 168, 170, 170, 173, 174, 176, 180, 182, 186, 188, 191, 198, 198, 208, 208, 215, 216, 222, 225, 230, 230, 232, 234, 236, 237, 240, 240, 242, 243, 247, 250, 252, 252, 254, 254, 257, 257, 273, 273, 275, 275, 283, 283, 294, 295, 299, 299, 305, 307, 312, 312, 319, 322, 324, 324, 328, 331, 333, 333, 338, 339, 358, 359, 363, 363, 462, 462, 464, 464, 466, 466, 468, 468, 470, 470, 472, 472, 474, 474, 476, 476, 593, 593, 609, 609, 708, 708, 711, 711, 713, 715, 717, 717, 720, 720, 728, 731, 733, 733, 735, 735, 768, 879, 913, 929, 931, 937, 945, 961, 963, 969, 1025, 1025, 1040, 1103, 1105, 1105, 8208, 8208, 8211, 8214, 8216, 8217, 8220, 8221, 8224, 8226, 8228, 8231, 8240, 8240, 8242, 8243, 8245, 8245, 8251, 8251, 8254, 8254, 8308, 8308, 8319, 8319, 8321, 8324, 8364, 8364, 8451, 8451, 8453, 8453, 8457, 8457, 8467, 8467, 8470, 8470, 8481, 8482, 8486, 8486, 8491, 8491, 8531, 8532, 8539, 8542, 8544, 8555, 8560, 8569, 8585, 8585, 8592, 8601, 8632, 8633, 8658, 8658, 8660, 8660, 8679, 8679, 8704, 8704, 8706, 8707, 8711, 8712, 8715, 8715, 8719, 8719, 8721, 8721, 8725, 8725, 8730, 8730, 8733, 8736, 8739, 8739, 8741, 8741, 8743, 8748, 8750, 8750, 8756, 8759, 8764, 8765, 8776, 8776, 8780, 8780, 8786, 8786, 8800, 8801, 8804, 8807, 8810, 8811, 8814, 8815, 8834, 8835, 8838, 8839, 8853, 8853, 8857, 8857, 8869, 8869, 8895, 8895, 8978, 8978, 9312, 9449, 9451, 9547, 9552, 9587, 9600, 9615, 9618, 9621, 9632, 9633, 9635, 9641, 9650, 9651, 9654, 9655, 9660, 9661, 9664, 9665, 9670, 9672, 9675, 9675, 9678, 9681, 9698, 9701, 9711, 9711, 9733, 9734, 9737, 9737, 9742, 9743, 9756, 9756, 9758, 9758, 9792, 9792, 9794, 9794, 9824, 9825, 9827, 9829, 9831, 9834, 9836, 9837, 9839, 9839, 9886, 9887, 9919, 9919, 9926, 9933, 9935, 9939, 9941, 9953, 9955, 9955, 9960, 9961, 9963, 9969, 9972, 9972, 9974, 9977, 9979, 9980, 9982, 9983, 10045, 10045, 10102, 10111, 11094, 11097, 12872, 12879, 57344, 63743, 65024, 65039, 65533, 65533, 127232, 127242, 127248, 127277, 127280, 127337, 127344, 127373, 127375, 127376, 127387, 127404, 917760, 917999, 983040, 1048573, 1048576, 1114109];
var fullwidthMinimalCodePoint = 12288;
var fullwidthMaximumCodePoint = 65510;
var fullwidthRanges = [12288, 12288, 65281, 65376, 65504, 65510];
var wideMinimalCodePoint = 4352;
var wideMaximumCodePoint = 262141;
var wideRanges = [4352, 4447, 8986, 8987, 9001, 9002, 9193, 9196, 9200, 9200, 9203, 9203, 9725, 9726, 9748, 9749, 9776, 9783, 9800, 9811, 9855, 9855, 9866, 9871, 9875, 9875, 9889, 9889, 9898, 9899, 9917, 9918, 9924, 9925, 9934, 9934, 9940, 9940, 9962, 9962, 9970, 9971, 9973, 9973, 9978, 9978, 9981, 9981, 9989, 9989, 9994, 9995, 10024, 10024, 10060, 10060, 10062, 10062, 10067, 10069, 10071, 10071, 10133, 10135, 10160, 10160, 10175, 10175, 11035, 11036, 11088, 11088, 11093, 11093, 11904, 11929, 11931, 12019, 12032, 12245, 12272, 12287, 12289, 12350, 12353, 12438, 12441, 12543, 12549, 12591, 12593, 12686, 12688, 12773, 12783, 12830, 12832, 12871, 12880, 42124, 42128, 42182, 43360, 43388, 44032, 55203, 63744, 64255, 65040, 65049, 65072, 65106, 65108, 65126, 65128, 65131, 94176, 94180, 94192, 94198, 94208, 101594, 101631, 101664, 101760, 101874, 101888, 102801, 102816, 102866, 110576, 110579, 110581, 110587, 110589, 110590, 110592, 110888, 110898, 110898, 110928, 110930, 110933, 110933, 110948, 110952, 110960, 111355, 119552, 119638, 119648, 119670, 126980, 126980, 127183, 127183, 127374, 127374, 127377, 127386, 127406, 127406, 127488, 127490, 127504, 127547, 127552, 127560, 127568, 127569, 127584, 127589, 127744, 127776, 127789, 127797, 127799, 127868, 127870, 127891, 127904, 127946, 127951, 127955, 127968, 127984, 127988, 127988, 127992, 128062, 128064, 128064, 128066, 128252, 128255, 128317, 128331, 128334, 128336, 128359, 128378, 128378, 128405, 128406, 128420, 128420, 128507, 128591, 128640, 128709, 128716, 128716, 128720, 128722, 128725, 128729, 128732, 128735, 128747, 128748, 128756, 128764, 128986, 128986, 128992, 129003, 129008, 129008, 129292, 129338, 129340, 129349, 129351, 129535, 129648, 129660, 129664, 129734, 129736, 129736, 129740, 129757, 129759, 129771, 129775, 129786, 131072, 196605, 196608, 262141];

// node_modules/get-east-asian-width/utilities.js
var isInRange = (ranges, codePoint) => {
  let low = 0;
  let high = Math.floor(ranges.length / 2) - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const i = mid * 2;
    if (codePoint < ranges[i]) {
      high = mid - 1;
    } else if (codePoint > ranges[i + 1]) {
      low = mid + 1;
    } else {
      return true;
    }
  }
  return false;
};

// node_modules/get-east-asian-width/lookup.js
var commonCjkCodePoint = 19968;
var [wideFastPathStart, wideFastPathEnd] = /* @__PURE__ */ findWideFastPathRange(wideRanges);
function findWideFastPathRange(ranges) {
  let fastPathStart = ranges[0];
  let fastPathEnd = ranges[1];
  for (let index = 0; index < ranges.length; index += 2) {
    const start = ranges[index];
    const end = ranges[index + 1];
    if (commonCjkCodePoint >= start && commonCjkCodePoint <= end) {
      return [start, end];
    }
    if (end - start > fastPathEnd - fastPathStart) {
      fastPathStart = start;
      fastPathEnd = end;
    }
  }
  return [fastPathStart, fastPathEnd];
}
var isAmbiguous = (codePoint) => {
  if (codePoint < ambiguousMinimalCodePoint || codePoint > ambiguousMaximumCodePoint) {
    return false;
  }
  return isInRange(ambiguousRanges, codePoint);
};
var isFullwidth = (codePoint) => {
  if (codePoint < fullwidthMinimalCodePoint || codePoint > fullwidthMaximumCodePoint) {
    return false;
  }
  return isInRange(fullwidthRanges, codePoint);
};
var isWide = (codePoint) => {
  if (codePoint >= wideFastPathStart && codePoint <= wideFastPathEnd) {
    return true;
  }
  if (codePoint < wideMinimalCodePoint || codePoint > wideMaximumCodePoint) {
    return false;
  }
  return isInRange(wideRanges, codePoint);
};

// node_modules/get-east-asian-width/index.js
function validate(codePoint) {
  if (!Number.isSafeInteger(codePoint)) {
    throw new TypeError(`Expected a code point, got \`${typeof codePoint}\`.`);
  }
}
function eastAsianWidth(codePoint, { ambiguousAsWide = false } = {}) {
  validate(codePoint);
  if (isFullwidth(codePoint) || isWide(codePoint) || ambiguousAsWide && isAmbiguous(codePoint)) {
    return 2;
  }
  return 1;
}

// node_modules/string-width/index.js
var import_emoji_regex = __toESM(require_emoji_regex(), 1);
var segmenter = new Intl.Segmenter();
var defaultIgnorableCodePointRegex = new RegExp("^\\p{Default_Ignorable_Code_Point}$", "u");
function stringWidth(string, options2 = {}) {
  if (typeof string !== "string" || string.length === 0) {
    return 0;
  }
  const {
    ambiguousIsNarrow = true,
    countAnsiEscapeCodes = false
  } = options2;
  if (!countAnsiEscapeCodes) {
    string = stripAnsi(string);
  }
  if (string.length === 0) {
    return 0;
  }
  let width = 0;
  const eastAsianWidthOptions = { ambiguousAsWide: !ambiguousIsNarrow };
  for (const { segment: character } of segmenter.segment(string)) {
    const codePoint = character.codePointAt(0);
    if (codePoint <= 31 || codePoint >= 127 && codePoint <= 159) {
      continue;
    }
    if (codePoint >= 8203 && codePoint <= 8207 || codePoint === 65279) {
      continue;
    }
    if (codePoint >= 768 && codePoint <= 879 || codePoint >= 6832 && codePoint <= 6911 || codePoint >= 7616 && codePoint <= 7679 || codePoint >= 8400 && codePoint <= 8447 || codePoint >= 65056 && codePoint <= 65071) {
      continue;
    }
    if (codePoint >= 55296 && codePoint <= 57343) {
      continue;
    }
    if (codePoint >= 65024 && codePoint <= 65039) {
      continue;
    }
    if (defaultIgnorableCodePointRegex.test(character)) {
      continue;
    }
    if ((0, import_emoji_regex.default)().test(character)) {
      width += 2;
      continue;
    }
    width += eastAsianWidth(codePoint, eastAsianWidthOptions);
  }
  return width;
}

// src/serial_diagnostics.js
import { execFile } from "node:child_process";
import { promisify } from "node:util";
var check = `import sys
try:
 import serial
except ModuleNotFoundError as error:
 sys.exit(71 if error.name == 'serial' else 73)
except Exception:
 sys.exit(73)
sys.exit(0 if callable(getattr(serial, 'Serial', None)) else 72)
`;
async function explainSerialFailure(failure3, options2, dependencies = {}) {
  if (failure3?.code === "SERIAL_BUSY") {
    failure3.message = "Serial port is busy. Close the IDE, serial monitor or other process using this port before retrying.";
    return failure3;
  }
  if (failure3?.code === "SERIAL_ACCESS_DENIED") {
    failure3.message = "Serial port access was denied. Check port permissions and close other applications using it; Windows may report an occupied port as access denied.";
    return failure3;
  }
  if (!["SERIAL_ERROR", "SERIAL_UNAVAILABLE"].includes(failure3?.code)) return failure3;
  if (dependencies.signal?.aborted) return failure3;
  if (["read", "write", "stdout", "stdin"].includes(failure3.details?.stage)) return failure3;
  let reason = "unknown";
  try {
    await (dependencies.execFile ?? promisify(execFile))(options2.python, ["-c", check], {
      signal: dependencies.signal,
      timeout: Math.min(options2.timeout ?? 3e3, 3e3),
      maxBuffer: 4096,
      windowsHide: true
    });
    reason = "available";
  } catch (cause) {
    if (dependencies.signal?.aborted) return failure3;
    if (cause.code === "ENOENT") reason = "missing-python";
    else if (cause.code === "EACCES") reason = "python-permission";
    else if (cause.code === 71) reason = "missing-pyserial";
    else if (cause.code === 72) reason = "invalid-pyserial";
    else if (cause.code === 73) reason = "import-failed";
  }
  const messages = {
    "missing-python": "The configured Python executable was not found. Check python3 --version (Windows: python --version or py --version), then select an installed interpreter with --python PATH; Windows Python Launcher users can use --python py.",
    "python-permission": "The configured Python executable could not be started because access was denied. Check executable permissions or select an accessible interpreter with --python PATH.",
    "missing-pyserial": 'The configured Python interpreter has no pyserial module. Install it in that same interpreter with PYTHON -m pip install pyserial (Windows Launcher: py -m pip install pyserial and --python py), then verify PYTHON -c "import serial". Replace PYTHON with the executable selected by --python.',
    "invalid-pyserial": "The configured Python imported a serial module without the pyserial Serial API. Check for a conflicting serial.py or serial package; verify pyserial in the interpreter selected by --python.",
    "import-failed": 'The configured Python could not import pyserial successfully. Run PYTHON -c "import serial" in the same interpreter to inspect the environment; select it with --python PATH.',
    available: "Python and the pyserial Serial API are available. Check the selected port, cable, OS permissions and whether another application owns the port. The serial failure does not establish a missing dependency.",
    unknown: 'Serial adapter failed; Python/pyserial availability could not be established. Check PYTHON --version and PYTHON -c "import serial", select that interpreter with --python PATH (Windows Launcher: --python py), and check port permissions and other applications using the port.'
  };
  failure3.message = messages[reason];
  return failure3;
}

// node_modules/@esp-vision/device-core/src/device_session.js
var EV_MUX_VERSION = 4;
var INLINE_PYTHON_REPL_TIMEOUT_MS = 5e3;
var SCRIPT_START_ACK_TIMEOUT_MS = 5e3;
var EV_MUX_PATH_MAX_BYTES = 123;
var EV_MUX_DEFAULT_LIMITS = Object.freeze({
  metadataMax: 384,
  rxPayloadMax: 2048,
  replInputMax: 511,
  vmPendingMax: 1,
  txLargePayloadMax: 0,
  txFrameTimeoutMs: 1500,
  txQueueTimeoutMs: 2e3
});
var EV_MUX_REQUIRED_FEATURES = [
  "capabilities",
  "route.changed",
  "framed.repl",
  "session.firstCome",
  "session.keepalive"
];
var EV_MUX_REQUIRED_CHANNELS = [
  "user.rpc",
  "debug.rpc",
  "repl.stdin",
  "repl.stdout",
  "repl.stderr",
  "repl.signal",
  "log.idf",
  "preview.frame"
];
var EV_MUX_USER_RPC_METHODS = /* @__PURE__ */ new Set([
  "hello",
  "capabilities",
  "session.keepalive",
  "session.release",
  "file.write",
  "script.write",
  "script.run",
  "device.control"
]);
function randomHex(bytes = 16) {
  const values = new Uint8Array(bytes);
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(values);
  } else {
    for (let i = 0; i < values.length; i += 1) values[i] = Math.floor(Math.random() * 256);
  }
  return Array.from(values, (value) => value.toString(16).padStart(2, "0")).join("");
}
function utf8Bytes(value) {
  return new TextEncoder().encode(value);
}
function decodeRpcPayload(payload) {
  if (payload instanceof Uint8Array) payload = new TextDecoder("utf-8", { fatal: false }).decode(payload);
  if (typeof payload !== "string") return payload && typeof payload === "object" ? payload : null;
  try {
    const value = JSON.parse(payload);
    return value && typeof value === "object" && !Array.isArray(value) ? value : null;
  } catch (_err) {
    return null;
  }
}
function validateLimit(limits, name) {
  const value = limits?.[name];
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`EV-MUX v4 capabilities are missing a valid limits.${name}`);
  }
  return value;
}
function responseVersion(payload) {
  return payload?.protocol?.evMuxVersion ?? payload?.evMuxVersion;
}
function unsupportedVersion(version) {
  const error2 = new Error(`Unsupported EV-MUX protocol: this host requires EV-MUX v4 firmware, but the device reported ${version ?? "an unknown version"}. Install firmware that explicitly supports EV-MUX v4.`);
  error2.code = "VERSION_MISMATCH";
  return error2;
}
function validateRpcPath(path) {
  if (typeof path !== "string" || path.length === 0) {
    const error2 = new Error("Device RPC path must be a non-empty string");
    error2.code = "INVALID_PATH";
    throw error2;
  }
  if (utf8Bytes(path).length > EV_MUX_PATH_MAX_BYTES) {
    const error2 = new Error(`Device RPC path exceeds the firmware limit of ${EV_MUX_PATH_MAX_BYTES} UTF-8 bytes`);
    error2.code = "PATH_TOO_LONG";
    throw error2;
  }
  const forbiddenCharacter = Array.from(path).some((character) => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127 || character === "\\" || character === '"');
  if (path.includes("..") || path.includes("//") || forbiddenCharacter) {
    const error2 = new Error("Device RPC path contains characters rejected by the firmware");
    error2.code = "INVALID_PATH";
    throw error2;
  }
}
function isVmEpoch(value) {
  return Number.isSafeInteger(value) && value >= 0 && value <= 4294967295;
}
function isPositiveVmEpoch(value) {
  return isVmEpoch(value) && value > 0;
}
function isVmEpochNewer(candidate, current) {
  if (!isVmEpoch(candidate) || !isVmEpoch(current) || candidate === current) return false;
  if (current === 0) return candidate > 0;
  if (candidate === 0) return false;
  const distance = candidate - current >>> 0;
  return distance > 0 && distance < 2147483648;
}
function isVmEpochAtLeast(candidate, current) {
  return isVmEpoch(candidate) && (current === null || candidate === current || isVmEpochNewer(candidate, current));
}
function isNetworkAction(method, payload) {
  if (method !== "device.control") return false;
  return typeof payload?.action === "string" && payload.action.startsWith("network.");
}
function isVmRpc(method, payload) {
  if (method === "file.write" || method === "script.write" || method === "script.run" || method === "debug.capture_frame" || method === "debug.capture_screen") return true;
  if (method === "debug.info") return payload?.scope !== "transport.stats";
  return false;
}
function payloadBytes(payload) {
  return payload instanceof Uint8Array ? payload : utf8Bytes(payload);
}
function defaultSleep(ms) {
  return new Promise((resolve2) => setTimeout(resolve2, ms));
}
function abortError(signal, fallback = "Device operation cancelled") {
  const reason = signal?.reason;
  if (reason instanceof Error) return reason;
  const error2 = new Error(typeof reason === "string" ? reason : fallback);
  error2.name = "AbortError";
  return error2;
}
function awaitWithSignal(promise, signal) {
  if (!signal) return Promise.resolve(promise);
  if (signal.aborted) return Promise.reject(abortError(signal));
  return new Promise((resolve2, reject) => {
    const cleanup = () => signal.removeEventListener("abort", onAbort);
    const onAbort = () => {
      cleanup();
      reject(abortError(signal));
    };
    signal.addEventListener("abort", onAbort, { once: true });
    Promise.resolve(promise).then((value) => {
      cleanup();
      resolve2(value);
    }, (error2) => {
      cleanup();
      reject(error2);
    });
  });
}
function createOperationDeadline(signal, timeout, timeoutError = Object.assign(new Error("Python execution timed out"), { code: "TIMEOUT" })) {
  if (timeout === null) return { signal, dispose() {
  } };
  const controller = new AbortController();
  const abortFromCaller = () => controller.abort(abortError(signal));
  signal?.addEventListener("abort", abortFromCaller, { once: true });
  if (signal?.aborted) abortFromCaller();
  const timer = controller.signal.aborted ? null : setTimeout(() => controller.abort(timeoutError), timeout);
  return {
    signal: controller.signal,
    dispose() {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abortFromCaller);
    }
  };
}
function withTimeout(operation, timeout, message, signal = null) {
  return new Promise((resolve2, reject) => {
    if (signal?.aborted) {
      reject(abortError(signal));
      return;
    }
    let settled = false;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      callback(value);
    };
    const timer = setTimeout(() => {
      const error2 = new Error(message);
      error2.code = "WRITE_TIMEOUT";
      finish(reject, error2);
    }, timeout);
    const onAbort = () => finish(reject, abortError(signal));
    signal?.addEventListener("abort", onAbort, { once: true });
    Promise.resolve().then(operation).then(
      (value) => finish(resolve2, value),
      (error2) => finish(reject, error2)
    );
  });
}
function validateEvmuxCapabilities(payload) {
  if (!payload || payload.ok !== true) {
    throw new Error("Missing EV-MUX capabilities");
  }
  const version = responseVersion(payload);
  if (version !== EV_MUX_VERSION) {
    throw unsupportedVersion(version);
  }
  const features = new Set(payload.features || []);
  const missing = EV_MUX_REQUIRED_FEATURES.filter((feature) => !features.has(feature));
  if (missing.length) {
    throw new Error(`Firmware is missing EV-MUX features: ${missing.join(", ")}. Please upgrade the ESP Vision firmware.`);
  }
  const channels = new Set(payload.channels || []);
  for (const channel of EV_MUX_REQUIRED_CHANNELS) {
    if (!channels.has(channel)) {
      throw new Error(`Firmware is missing EV-MUX channel: ${channel}. Please upgrade the ESP Vision firmware.`);
    }
  }
  for (const key of Object.keys(EV_MUX_DEFAULT_LIMITS)) validateLimit(payload.limits, key);
  if (payload.features.includes("file.write.binary") && (!Number.isSafeInteger(payload.limits.fileWriteChunkMax) || payload.limits.fileWriteChunkMax < 4096 || payload.limits.fileWriteChunkMax > 16384 || payload.limits.fileWriteChunkMax % 4096 !== 0)) {
    throw new Error("EV-MUX v4 capabilities are missing a valid limits.fileWriteChunkMax");
  }
  if (payload.session?.policy !== "firstCome" || !Number.isSafeInteger(payload.session.leaseMs) || !Number.isSafeInteger(payload.session.keepaliveMs) || payload.session.keepaliveMs <= 0 || payload.session.leaseMs < payload.session.keepaliveMs * 2) {
    throw new Error("EV-MUX v4 capabilities are missing a valid first-come session lease");
  }
}
function evmuxRpcChannelForMethod(method) {
  return EV_MUX_USER_RPC_METHODS.has(method) ? "user.rpc" : "debug.rpc";
}
function evmuxLogicalSidForChannel(channel) {
  return channel === "debug.rpc" ? "debug" : "user";
}
var DeviceSession = class {
  constructor({
    transport,
    EvMuxParser: EvMuxParser2,
    makeEvMuxFrame: makeEvMuxFrame2,
    EvRepl: EvRepl2,
    handlers = {},
    sid = "ide-client",
    sleep = defaultSleep
  }) {
    if (!transport?.writeBytes) {
      throw new Error("DeviceSession requires a byte transport");
    }
    if (!EvMuxParser2 || !makeEvMuxFrame2 || !EvRepl2) {
      throw new Error("DeviceSession requires the shared EV-MUX parser and REPL interpreter");
    }
    this.transport = transport;
    this.makeEvMuxFrame = makeEvMuxFrame2;
    this.handlers = handlers;
    this.sid = sid;
    this.sleep = sleep;
    this.sequence = 1;
    this.clientNonce = randomHex();
    this.state = "disconnected";
    this.role = "unknown";
    this.capabilities = null;
    this.identity = null;
    this.limits = { ...EV_MUX_DEFAULT_LIMITS };
    this.sessionId = null;
    this.vmEpoch = null;
    this.vmReady = false;
    this.vmReadyKnown = false;
    this.keepaliveMs = 5e3;
    this.leaseMs = 15e3;
    this.keepaliveTimer = null;
    this.keepaliveGeneration = 0;
    this.sessionGeneration = 0;
    this.negotiatePromise = null;
    this.negotiateController = null;
    this.releasePromise = null;
    this.vmReadinessProbeActive = false;
    this.pendingRpc = /* @__PURE__ */ new Map();
    this.draining = false;
    this.lastDebugImage = null;
    this.runCapture = null;
    this.runStarting = false;
    this.repl = new EvRepl2({
      writeEvmux: (channel, type, method, payload, options2) => this.writeFrame(channel, type, method, payload, options2)
    });
    this.repl.onScriptEnd = () => this._handleScriptEnd();
    this.parser = new EvMuxParser2({
      filterFrame: (metadata, payload) => this._acceptInboundFrame(metadata, payload),
      text: (text) => {
        const passthrough = this.repl.feedStdout(text);
        if (passthrough) {
          if (this.runCapture) {
            const remaining = this.runCapture.maxOutputChars - this.runCapture.output.length;
            if (remaining > 0) this.runCapture.output += passthrough.slice(0, remaining);
            if (passthrough.length > remaining) this.runCapture.outputTruncated = true;
          }
          this.handlers.text?.(passthrough);
        }
      },
      rawText: (text) => this.handlers.rawText?.(text),
      preview: (base64, metadata, bytes) => this.handlers.preview?.(base64, metadata, bytes),
      debugImage: (base64, metadata, bytes, frameMetadata) => {
        this.lastDebugImage = { base64, metadata };
        const pending = this.pendingRpc.get(Number(metadata.seq));
        if (pending?.binaryResponse && frameMetadata && this._matchesPendingResponse(frameMetadata, { ok: true })) {
          pending.image = { data: bytes.slice(), mimeType: "image/jpeg", metadata: { ...metadata } };
        }
        this.handlers.debugImage?.(base64, metadata);
      },
      log: (text) => this.handlers.log?.(text),
      command: (text) => this.handlers.command?.(text),
      other: (text) => this.handlers.other?.(text),
      rpc: (metadata, payload) => this._handleRpc(metadata, payload)
    });
  }
  _diagnostic(event, details = {}) {
    this.handlers.diagnostic?.({ event, ...details });
  }
  _matchesPendingResponse(metadata, payload) {
    const seq = Number(metadata.seq);
    const pending = this.pendingRpc.get(seq);
    if (!pending || pending.channel !== metadata.channel || pending.method !== metadata.method) return false;
    const response = decodeRpcPayload(payload);
    if (pending.sessionId) {
      if (response?.ok === false && metadata.sessionId === void 0 && metadata.vmEpoch === void 0 && ["SESSION_REQUIRED", "SESSION_EXPIRED", "NOT_OWNER"].includes(response.error?.code)) return true;
      if (metadata.sessionId !== pending.sessionId) return false;
      if (pending.vmRequest) {
        if (!isPositiveVmEpoch(metadata.vmEpoch) || metadata.vmEpoch !== pending.vmEpoch) return false;
      } else if (!isVmEpoch(metadata.vmEpoch)) {
        return false;
      }
      if (pending.method === "session.keepalive" && response?.ok === true) {
        if (!isVmEpoch(response.vmEpoch) || response.vmEpoch !== metadata.vmEpoch) return false;
        if (response.sessionId !== void 0 && response.sessionId !== pending.sessionId) return false;
      }
    } else if (pending.acquireSession) {
      if (response?.ok === false) {
        return metadata.sessionId === void 0 && metadata.vmEpoch === void 0;
      }
      const version = responseVersion(response);
      if (response?.ok === true && Number.isSafeInteger(version) && version !== EV_MUX_VERSION) {
        return metadata.sessionId === void 0 && metadata.vmEpoch === void 0;
      }
      const responseSessionId = response?.session?.id;
      const responseEpoch = response?.session?.vmEpoch;
      if (!/^[0-9a-f]{32}$/.test(responseSessionId || "") || metadata.sessionId !== responseSessionId || !isVmEpoch(responseEpoch) || metadata.vmEpoch !== responseEpoch) return false;
    } else if (metadata.sessionId !== void 0 || metadata.vmEpoch !== void 0) {
      return false;
    }
    return true;
  }
  _acceptInboundFrame(metadata, payload) {
    if (this.draining) return false;
    const channel = metadata.channel || "";
    const type = metadata.type || "";
    if (channel === "log.idf") return true;
    if (channel === "user.rpc" || channel === "debug.rpc") {
      if (type === "rsp") return this._matchesPendingResponse(metadata, payload);
      if (type !== "event") return false;
      const eventPayload = decodeRpcPayload(payload);
      if (metadata.method === "hello") {
        if (!this.sessionId || responseVersion(eventPayload) !== EV_MUX_VERSION) return false;
        const eventSessionId = eventPayload?.session?.id;
        const sessionEpoch = eventPayload?.session?.vmEpoch;
        const payloadEpoch = eventPayload?.vmEpoch;
        return metadata.sessionId === this.sessionId && eventSessionId === this.sessionId && isVmEpoch(sessionEpoch) && sessionEpoch === payloadEpoch && payloadEpoch === metadata.vmEpoch && isVmEpochAtLeast(sessionEpoch, this.vmEpoch);
      }
      if (!this.sessionId) return false;
      if (metadata.sessionId !== this.sessionId || !isVmEpoch(metadata.vmEpoch)) return false;
      return Boolean(metadata.method);
    }
    if (channel === "repl.stdout" || channel === "repl.stderr") {
      return Boolean(this.sessionId) && (this.vmReady || this.vmReadinessProbeActive) && isPositiveVmEpoch(this.vmEpoch) && metadata.sessionId === this.sessionId && metadata.vmEpoch === this.vmEpoch;
    }
    if (channel === "preview.frame") {
      return Boolean(this.sessionId) && this.vmReady && isPositiveVmEpoch(this.vmEpoch) && metadata.sessionId === this.sessionId && metadata.vmEpoch === this.vmEpoch;
    }
    return false;
  }
  _handleRpc(metadata, payload) {
    const seq = Number(metadata.seq);
    const channel = metadata.channel || "user.rpc";
    let requestPayload = null;
    let callbackPayload = payload;
    if (metadata.type === "event") {
      if (metadata.method === "hello") this._handleHelloEvent(payload);
      callbackPayload = metadata.method === "network.changed" ? this._redactRpcPayload("device.control", { action: "network.status", ...payload }) : payload;
      this.handlers.rpcEvent?.({ channel, metadata, payload: callbackPayload });
    } else if (metadata.type === "rsp") {
      const pending = this.pendingRpc.get(seq);
      if (pending && this._matchesPendingResponse(metadata, payload)) {
        requestPayload = pending.requestPayload;
        this.pendingRpc.delete(seq);
        pending.resolve({ metadata, payload, image: pending.image });
      } else {
        this.handlers.rpcOrphan?.({
          channel,
          metadata,
          payload: this._redactRpcPayload(metadata.method, payload, {
            forceNetwork: metadata.method === "device.control"
          })
        });
      }
      callbackPayload = this._redactRpcPayload(metadata.method, payload, {
        requestPayload,
        forceNetwork: metadata.method === "device.control" && requestPayload === null
      });
    }
    this.handlers.rpc?.({
      channel,
      metadata,
      payload: callbackPayload
    });
    return false;
  }
  _handleHelloEvent(payload) {
    if (!payload || responseVersion(payload) !== EV_MUX_VERSION) return;
    const eventSession = payload.session;
    const epoch = eventSession?.vmEpoch;
    if (!this.sessionId || eventSession?.id !== this.sessionId) return;
    if (!isVmEpoch(epoch) || epoch !== payload.vmEpoch || !isVmEpochAtLeast(epoch, this.vmEpoch)) return;
    this._updateVmEpoch(epoch, "device soft reset");
    if (typeof payload.vmReady === "boolean") this._setVmReady(payload.vmReady);
  }
  _updateVmEpoch(epoch, reason = "VM epoch changed") {
    if (!isVmEpoch(epoch)) return false;
    if (this.vmEpoch !== null && epoch !== this.vmEpoch && !isVmEpochNewer(epoch, this.vmEpoch)) return false;
    if (this.vmEpoch === epoch) return false;
    const previous = this.vmEpoch;
    this.vmEpoch = epoch;
    this.vmReady = false;
    if (previous !== null) {
      const error2 = new Error(`${reason}; pending VM requests were cleared`);
      error2.code = "VM_EPOCH_CHANGED";
      for (const [seq, pending] of this.pendingRpc) {
        if (!pending.vmRequest) continue;
        this.pendingRpc.delete(seq);
        pending.reject(error2);
      }
      this.runCapture?.reject(error2);
      if (this.runCapture) {
        clearTimeout(this.runCapture.timer);
        this.runCapture = null;
        this.repl.cancelScriptEndSentinel(error2);
      }
      this.parser.resetReplTextDecoders?.();
      this.repl.resetEpoch(error2);
      this._diagnostic("session.vm_epoch_changed", { previous, current: epoch });
    }
    return true;
  }
  _setVmReady(ready) {
    this.vmReadyKnown = true;
    this.vmReady = ready === true && isPositiveVmEpoch(this.vmEpoch);
    return this.vmReady;
  }
  async _keepaliveOnce({ sessionId, generation, keepaliveGeneration }) {
    try {
      return await this.rpc("session.keepalive", {}, { timeout: 3e3 });
    } catch (error2) {
      if (error2.code !== "TIMEOUT" || this.leaseMs <= this.keepaliveMs + 6e3 || this.sessionId !== sessionId || this.sessionGeneration !== generation || this.keepaliveGeneration !== keepaliveGeneration || this.state === "disconnected") throw error2;
      this._diagnostic("session.keepalive_retry", { code: error2.code });
      return this.rpc("session.keepalive", {}, { timeout: 3e3 });
    }
  }
  _startKeepalive() {
    clearTimeout(this.keepaliveTimer);
    this.keepaliveGeneration += 1;
    if (!this.sessionId || this.keepaliveMs <= 0) return;
    const sessionId = this.sessionId;
    const generation = this.sessionGeneration;
    const keepaliveGeneration = this.keepaliveGeneration;
    const tick = async () => {
      if (this.sessionId !== sessionId || this.sessionGeneration !== generation || this.keepaliveGeneration !== keepaliveGeneration || this.state === "disconnected") return;
      try {
        const response = await this._keepaliveOnce({ sessionId, generation, keepaliveGeneration });
        if (this.sessionId !== sessionId || this.sessionGeneration !== generation || this.keepaliveGeneration !== keepaliveGeneration) return;
        if (response.sessionId && response.sessionId !== sessionId) {
          throw new Error("EV-MUX keepalive returned a different session ID");
        }
        const responseEpoch = isVmEpoch(response.vmEpoch) ? response.vmEpoch : this.vmEpoch;
        this._updateVmEpoch(responseEpoch, "VM epoch changed");
        if (responseEpoch === this.vmEpoch && typeof response.vmReady === "boolean") {
          this._setVmReady(response.vmReady);
        }
      } catch (error2) {
        if (this.sessionId === sessionId && this.sessionGeneration === generation && this.keepaliveGeneration === keepaliveGeneration) {
          this._diagnostic("session.keepalive_failed", { code: error2.code || "ERROR", message: error2.message });
          this.close(error2);
          this.handlers.sessionLost?.(error2);
        }
        return;
      }
      if (this.sessionId !== sessionId || this.sessionGeneration !== generation || this.keepaliveGeneration !== keepaliveGeneration || this.state === "disconnected") return;
      this.keepaliveTimer = setTimeout(tick, this.keepaliveMs);
      this.keepaliveTimer.unref?.();
    };
    this.keepaliveTimer = setTimeout(tick, this.keepaliveMs);
    this.keepaliveTimer.unref?.();
  }
  _allocateSequence() {
    for (let attempt = 0; attempt < 4294967296; attempt += 1) {
      const seq = this.sequence >>> 0;
      this.sequence = seq + 1 >>> 0;
      if (!this.pendingRpc.has(seq)) return seq;
    }
    throw new Error("EV-MUX request sequence space is exhausted");
  }
  _redactRpcPayload(method, payload, {
    requestPayload = null,
    redactSsid = true,
    forceNetwork = false
  } = {}) {
    if (payload instanceof Uint8Array) return { binaryBytes: payload.byteLength };
    if (!forceNetwork && !isNetworkAction(method, payload) && !isNetworkAction(method, requestPayload)) return payload;
    const secrets = [requestPayload?.ssid, requestPayload?.password].filter((value) => typeof value === "string" && value.length > 0);
    const sanitize = (value, key = "") => {
      if (key.toLowerCase() === "password" || redactSsid && key.toLowerCase() === "ssid") {
        return "[redacted]";
      }
      if (key.toLowerCase() === "message") {
        return "Wi-Fi operation failed. Use the error code to diagnose it.";
      }
      if (typeof value === "string") {
        return secrets.reduce((result, secret) => result.split(secret).join("[redacted]"), value);
      }
      if (Array.isArray(value)) return value.map((item) => sanitize(item));
      if (value && typeof value === "object") {
        return Object.fromEntries(Object.entries(value).map(([childKey, childValue]) => [
          childKey,
          sanitize(childValue, childKey)
        ]));
      }
      return value;
    };
    return sanitize(payload);
  }
  _handleScriptEnd() {
    const capture = this.runCapture;
    if (!capture) {
      this.handlers.scriptEnd?.();
      return;
    }
    clearTimeout(capture.timer);
    queueMicrotask(() => {
      if (this.runCapture !== capture) return;
      this.runCapture = null;
      this.handlers.scriptEnd?.();
      capture.resolve({
        ok: true,
        path: capture.path,
        output: capture.output.replace(/\r/g, ""),
        outputTruncated: capture.outputTruncated
      });
    });
  }
  feedBytes(bytes) {
    this.parser.feedBytes(bytes);
  }
  feedText(text) {
    this.parser.feedText(text);
  }
  hasFeature(feature) {
    return Boolean(this.capabilities?.features?.includes(feature));
  }
  async writeFrame(channel, type, method, payload, {
    authorize = null,
    vmRequest = null,
    seq: requestedSeq = null,
    signal = null,
    writeTimeout = null,
    encoding = void 0
  } = {}) {
    if (this.state === "disconnected") {
      throw new Error("EV-MUX is not connected");
    }
    const seq = requestedSeq === null ? this._allocateSequence() : requestedSeq >>> 0;
    const requestPayload = typeof payload === "string" && method ? (() => {
      try {
        return JSON.parse(payload);
      } catch (_err) {
        return {};
      }
    })() : payload;
    const needsAuthorization = authorize ?? !(method === "hello" || method === "capabilities");
    const usesVm = vmRequest ?? (channel === "repl.stdin" || channel === "repl.signal" || Boolean(method) && isVmRpc(method, requestPayload));
    if (needsAuthorization && !this.sessionId) {
      throw new Error(`EV-MUX ${method || channel} requires an acquired v4 session`);
    }
    const readinessProbe = this.vmReadinessProbeActive;
    if (usesVm && needsAuthorization) {
      if (!isPositiveVmEpoch(this.vmEpoch)) {
        throw new Error(`EV-MUX ${method || channel} requires a positive VM epoch`);
      }
      if (!this.vmReady && !readinessProbe) {
        throw new Error(`EV-MUX ${method || channel} requires a ready VM`);
      }
    }
    const payloadData = payloadBytes(payload);
    if (channel === "repl.signal" && (payloadData.length !== 1 || payloadData[0] !== 3)) {
      throw new Error("EV-MUX repl.signal only accepts the single-byte Ctrl-C signal 0x03");
    }
    const payloadLimit = method === "file.write" && encoding === "binary" && this.hasFeature("file.write.binary") ? this.limits.fileWriteChunkMax + 20 : this.limits.rxPayloadMax;
    if (this.capabilities && payloadData.length > payloadLimit) {
      throw new Error(`EV-MUX payload is ${payloadData.length} bytes; device limit is ${this.limits.rxPayloadMax}`);
    }
    if ((channel === "repl.stdin" || channel === "repl.signal") && payloadData.length > this.limits.replInputMax) {
      throw new Error(`EV-MUX REPL input is ${payloadData.length} bytes; device limit is ${this.limits.replInputMax}`);
    }
    const frameType = channel === "repl.stdin" || channel === "repl.signal" ? "req" : type;
    const metadata = {
      sid: evmuxLogicalSidForChannel(channel),
      seq,
      channel,
      type: frameType,
      encoding: encoding ?? (channel.endsWith(".rpc") ? "json" : "text"),
      ...method ? { method } : {},
      ...needsAuthorization ? { sessionId: this.sessionId } : {},
      ...usesVm && needsAuthorization ? { vmEpoch: this.vmEpoch } : {}
    };
    if (utf8Bytes(JSON.stringify(metadata)).length > this.limits.metadataMax) {
      throw new Error(`EV-MUX metadata exceeds device limit ${this.limits.metadataMax}`);
    }
    const frame = this.makeEvMuxFrame({
      channel,
      type: frameType,
      encoding,
      method,
      payload,
      seq,
      sid: evmuxLogicalSidForChannel(channel),
      sessionId: needsAuthorization ? this.sessionId : void 0,
      vmEpoch: usesVm && needsAuthorization ? this.vmEpoch : void 0
    });
    const boundedWriteTimeout = Math.max(1, Math.min(
      writeTimeout ?? Number.MAX_SAFE_INTEGER,
      (this.limits.txFrameTimeoutMs || EV_MUX_DEFAULT_LIMITS.txFrameTimeoutMs) + (this.limits.txQueueTimeoutMs || EV_MUX_DEFAULT_LIMITS.txQueueTimeoutMs)
    ));
    await withTimeout(
      () => this.transport.writeBytes(frame),
      boundedWriteTimeout,
      "EV-MUX transport write timeout",
      signal
    );
    return seq;
  }
  async rpc(method, payload = {}, { timeout = 4e3, channel = null, signal = null, binaryResponse = false } = {}) {
    if (this.state === "disconnected") {
      throw new Error("EV-MUX is not connected");
    }
    if (signal?.aborted) throw abortError(signal);
    if (payload instanceof Uint8Array && method !== "file.write") throw new TypeError("Raw binary requests are only supported for file.write");
    if (method === "script.write" || method === "script.run") validateRpcPath(payload?.path);
    if (method === "debug.info" && (payload?.scope === "fs.list" || payload?.scope === "fs.read")) {
      validateRpcPath(payload.path ?? (payload.scope === "fs.list" ? "/" : void 0));
    }
    const rpcChannel = channel || evmuxRpcChannelForMethod(method);
    const seq = this._allocateSequence();
    const vmRequest = isVmRpc(method, payload);
    const response = new Promise((resolve2, reject) => {
      const timer = setTimeout(() => {
        this.pendingRpc.delete(seq);
        cleanup();
        this.handlers.rpcTimeout?.({ channel: rpcChannel, method, seq, timeout });
        const error2 = new Error(`EV-MUX ${method} timeout`);
        error2.code = "TIMEOUT";
        reject(error2);
      }, timeout);
      const onAbort = () => {
        this.pendingRpc.delete(seq);
        clearTimeout(timer);
        cleanup();
        reject(abortError(signal));
      };
      signal?.addEventListener("abort", onAbort, { once: true });
      const cleanup = () => signal?.removeEventListener("abort", onAbort);
      this.pendingRpc.set(seq, {
        method,
        channel: rpcChannel,
        vmRequest,
        sessionId: method === "hello" || method === "capabilities" ? null : this.sessionId,
        vmEpoch: method === "hello" || method === "capabilities" ? null : this.vmEpoch,
        acquireSession: method === "hello" && payload?.acquire === true,
        requestPayload: payload,
        binaryResponse,
        timer,
        resolve: (value) => {
          clearTimeout(timer);
          cleanup();
          resolve2(value);
        },
        reject: (error2) => {
          clearTimeout(timer);
          cleanup();
          reject(error2);
        }
      });
    });
    const safePayload = this._redactRpcPayload(method, payload);
    this.handlers.rpcRequest?.({ channel: rpcChannel, method, seq, timeout, payload: safePayload });
    this._diagnostic("rpc.request", { channel: rpcChannel, method, seq });
    try {
      await this.writeFrame(rpcChannel, "req", method, payload instanceof Uint8Array ? payload : JSON.stringify(payload), {
        encoding: payload instanceof Uint8Array ? "binary" : void 0,
        vmRequest,
        seq,
        signal,
        writeTimeout: timeout
      });
    } catch (err) {
      const pending = this.pendingRpc.get(seq);
      this.pendingRpc.delete(seq);
      pending?.reject(err);
      this.handlers.rpcWriteError?.({ channel: rpcChannel, method, seq, error: err });
      try {
        await response;
      } catch (_err) {
      }
      throw err;
    }
    const { metadata, payload: responsePayload, image } = await response;
    const safeResponse = this._redactRpcPayload(method, responsePayload, { requestPayload: payload });
    this.handlers.rpcResponse?.({ channel: rpcChannel, method, seq, metadata, payload: safeResponse });
    this._diagnostic("rpc.response", { channel: rpcChannel, method, seq, ok: responsePayload?.ok });
    if (!responsePayload?.ok) {
      const safeError = this._redactRpcPayload(method, responsePayload, { requestPayload: payload });
      const error2 = new Error(safeError?.error?.message || `${method} failed`);
      error2.code = responsePayload?.error?.code || "RPC_ERROR";
      error2.response = safeError;
      throw error2;
    }
    if (binaryResponse) {
      if (!image) throw Object.assign(new Error("Capture returned no binary image"), { code: "INVALID_RESPONSE" });
      return image;
    }
    return this._redactRpcPayload(method, responsePayload, { requestPayload: payload, redactSsid: false });
  }
  captureImage(method, payload = {}, options2 = {}) {
    return this.rpc(method, payload, { ...options2, channel: "debug.rpc", binaryResponse: true });
  }
  negotiate(options2 = {}) {
    if (this.negotiatePromise) return this.negotiatePromise;
    if (this.releasePromise) return Promise.reject(new Error("EV-MUX session is being released"));
    const controller = new AbortController();
    const callerSignal = options2.signal || null;
    const abortFromCaller = () => controller.abort(callerSignal.reason);
    if (callerSignal?.aborted) abortFromCaller();
    else callerSignal?.addEventListener("abort", abortFromCaller, { once: true });
    this.negotiateController = controller;
    const deadlineError = new Error("EV-MUX negotiation deadline exceeded");
    deadlineError.code = "TIMEOUT";
    const deadlineTimer = setTimeout(() => controller.abort(deadlineError), 3e4);
    const operation = this._negotiate({ ...options2, signal: controller.signal });
    const tracked = operation.finally(() => {
      clearTimeout(deadlineTimer);
      callerSignal?.removeEventListener("abort", abortFromCaller);
      if (this.negotiatePromise === tracked) this.negotiatePromise = null;
      if (this.negotiateController === controller) this.negotiateController = null;
      if (this.state === "negotiating" && !this.sessionId) this.state = "disconnected";
    });
    this.negotiatePromise = tracked;
    return tracked;
  }
  async _negotiate({ role = "unknown", drainMs = 300, signal = null, acquire = true, probeRepl = true, expectedDevice = null } = {}) {
    this.role = role;
    this.state = "negotiating";
    this._diagnostic("negotiate.begin", { role });
    if (role === "tcp") drainMs = 0;
    if (drainMs > 0) {
      this.draining = true;
      try {
        await awaitWithSignal(this.sleep(drainMs), signal);
      } finally {
        this.draining = false;
      }
    }
    if (signal?.aborted) throw abortError(signal);
    if (drainMs > 0 && this.parser.hasPartialFrame?.()) {
      const error2 = Object.assign(new Error("Incomplete EV-MUX frame at end of startup drain"), {
        code: "SERIAL_STARTUP_INCOMPLETE_FRAME"
      });
      this.close(error2);
      this.parser.reset();
      await this.transport.disconnect?.();
      throw error2;
    }
    let capabilities;
    let discovery;
    let hello = null;
    if (expectedDevice) {
      const candidate = await this.rpc("hello", {}, { timeout: 1500, signal });
      if (responseVersion(candidate) !== EV_MUX_VERSION) throw unsupportedVersion(responseVersion(candidate));
      if (candidate.deviceId !== expectedDevice.deviceId || candidate.hostname !== expectedDevice.hostname) {
        const error2 = new Error("Selected device identity does not match the connected firmware");
        error2.code = "DEVICE_IDENTITY_MISMATCH";
        throw error2;
      }
    }
    if (acquire) {
      const acquirePayload = {
        evMuxVersion: EV_MUX_VERSION,
        acquire: true,
        clientNonce: this.clientNonce
      };
      const acquireDeadline = Date.now() + 4e3;
      let timeoutReplayAttempted = false;
      while (true) {
        const remainingMs = acquireDeadline - Date.now();
        if (remainingMs <= 0) {
          const error2 = new Error("EV-MUX session acquisition deadline exceeded");
          error2.code = "TIMEOUT";
          throw error2;
        }
        try {
          hello = await this.rpc("hello", acquirePayload, {
            // Leave time to replay a lost acknowledgement with the same nonce.
            timeout: Math.min(timeoutReplayAttempted ? 4e3 : 2e3, remainingMs),
            signal,
            channel: "user.rpc"
          });
          break;
        } catch (error2) {
          if (signal?.aborted) throw abortError(signal);
          if (error2.code === "TIMEOUT" && !timeoutReplayAttempted) {
            timeoutReplayAttempted = true;
            continue;
          }
          if (error2.code !== "SESSION_RELEASING") throw error2;
          const retryDelayMs = Math.min(10, Math.max(0, acquireDeadline - Date.now()));
          if (retryDelayMs <= 0) throw error2;
          await awaitWithSignal(this.sleep(retryDelayMs), signal);
        }
      }
      if (responseVersion(hello) !== EV_MUX_VERSION) throw unsupportedVersion(responseVersion(hello));
      if (!hello.session || typeof hello.session.id !== "string") {
        throw new Error("EV-MUX v4 acquire response did not include an active session");
      }
      if (!/^[0-9a-f]{32}$/.test(hello.session.id) || !isVmEpoch(hello.session.vmEpoch)) {
        throw new Error("EV-MUX v4 acquire response contains an invalid session ID or VM epoch");
      }
      if (this.sessionId !== hello.session.id) this.sessionGeneration += 1;
      this.sessionId = hello.session.id;
      this._updateVmEpoch(hello.session.vmEpoch);
      this.vmReadyKnown = typeof hello.vmReady === "boolean";
      if (this.vmReadyKnown) this._setVmReady(hello.vmReady);
      this.keepaliveMs = hello.session.keepaliveMs || this.keepaliveMs;
      this.leaseMs = hello.session.leaseMs || this.leaseMs;
      this.parser.active = true;
      this.state = "ready";
      this._startKeepalive();
    }
    try {
      capabilities = await this.rpc("capabilities", {}, { timeout: 6e3, signal });
      validateEvmuxCapabilities(capabilities);
      discovery = await this.rpc("hello", {}, { timeout: 6e3, signal });
    } catch (err) {
      this._diagnostic("negotiate.discovery_failed", {
        parser: this.parser.getDiagnostics?.(),
        transport: this.transport.getDiagnostics?.(),
        sessionAcquired: Boolean(this.sessionId)
      });
      throw err;
    }
    if (discovery.evMuxVersion !== EV_MUX_VERSION) {
      throw unsupportedVersion(responseVersion(discovery));
    }
    if (expectedDevice && (discovery.deviceId !== expectedDevice.deviceId || discovery.hostname !== expectedDevice.hostname)) {
      const error2 = new Error("Selected device identity does not match the connected firmware");
      error2.code = "DEVICE_IDENTITY_MISMATCH";
      throw error2;
    }
    this.identity = {
      deviceId: discovery.deviceId ?? null,
      hostname: discovery.hostname ?? null,
      board: discovery.board,
      firmwareVersion: discovery.firmware?.version
    };
    this.capabilities = capabilities;
    this.limits = { ...EV_MUX_DEFAULT_LIMITS, ...capabilities.limits };
    this.keepaliveMs = capabilities.session.keepaliveMs;
    this.leaseMs = capabilities.session.leaseMs;
    this.repl.inputMaxBytes = this.limits.replInputMax;
    this.parser.setLimits?.({
      metadataMax: this.limits.metadataMax,
      payloadMax: Math.max(this.limits.rxPayloadMax, this.limits.txLargePayloadMax),
      frameProgressTimeoutMs: 12e3,
      frameTotalTimeoutMs: 12e3
    });
    if (acquire) {
      this._startKeepalive();
    } else {
      this.parser.active = true;
      this.state = "discovered";
      this._diagnostic("negotiate.discovered", { role });
      return { hello: discovery, discovery, capabilities };
    }
    if (!probeRepl) {
      this.parser.active = true;
      this.state = acquire ? "ready" : "discovered";
      this._diagnostic("negotiate.ready_readonly", { role });
      return { hello, discovery, capabilities };
    }
    const canUseReadinessBarrier = acquire && isPositiveVmEpoch(this.vmEpoch) && (!this.vmReadyKnown || this.vmReady);
    if (canUseReadinessBarrier) {
      this.vmReadinessProbeActive = true;
      try {
        await this.writeFrame("repl.signal", "signal", null, new Uint8Array([3]), { signal });
        const liveness = await this.repl.execPy('print("EVIDE_BOOT_OK")', { timeout: 1e4, signal });
        if (!liveness.includes("EVIDE_BOOT_OK")) {
          throw new Error("EV-MUX REPL liveness check failed");
        }
        if (!this.vmReadyKnown) this._setVmReady(true);
      } finally {
        this.vmReadinessProbeActive = false;
      }
    } else if (acquire && !this.vmReady) {
      this._diagnostic("negotiate.vm_not_ready", { vmEpoch: this.vmEpoch });
    }
    this.parser.active = true;
    this.state = acquire ? "ready" : "discovered";
    this._diagnostic("negotiate.ready", { role });
    return { hello, discovery, capabilities };
  }
  async writeFile(path, content, {
    encoding = "utf-8",
    mode = "overwrite",
    runAfterWrite = false,
    signal = null,
    onProgress = null
  } = {}) {
    if (signal?.aborted) throw abortError(signal);
    validateRpcPath(path);
    if (!["utf-8", "binary"].includes(encoding)) {
      throw new Error(`Unsupported device file encoding: ${encoding}`);
    }
    if (!["create", "overwrite"].includes(mode)) {
      throw new Error(`Unsupported device file mode: ${mode}`);
    }
    if (encoding === "binary" && runAfterWrite) {
      throw new Error("Binary device files cannot run after write");
    }
    const bytes = typeof content === "string" ? new TextEncoder().encode(content) : content instanceof Uint8Array ? content : new Uint8Array(content);
    if (!this.hasFeature("file.write.binary")) {
      throw Object.assign(new Error("File upload requires firmware with file.write.binary; update the device firmware"), { code: "UNSUPPORTED_OPERATION" });
    }
    const limit = this.limits.fileWriteChunkMax;
    if (!Number.isSafeInteger(limit) || limit < 4096 || limit > 16384 || limit % 4096 !== 0 || bytes.length > 4294967295) {
      throw new Error("Invalid negotiated binary file transfer limit or file size");
    }
    const digest = new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", bytes));
    if (signal?.aborted) throw abortError(signal);
    const sha256 = Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("");
    const uploadId = randomHex();
    let committed = false;
    try {
      const begin = await this.rpc("file.write", { action: "begin", path, mode, totalBytes: bytes.length, sha256, uploadId }, { timeout: 8e3, signal });
      if (begin.uploadId !== uploadId || begin.chunkBytes !== limit) throw new Error("Invalid binary file transfer acknowledgement");
      const token = Uint8Array.from(begin.uploadId.match(/../g), (byte) => parseInt(byte, 16));
      for (let offset = 0; offset < bytes.length; offset += limit) {
        if (signal?.aborted) throw abortError(signal);
        const chunk = bytes.subarray(offset, Math.min(offset + limit, bytes.length));
        const payload = new Uint8Array(20 + chunk.length);
        payload.set(token);
        new DataView(payload.buffer).setUint32(16, offset, true);
        payload.set(chunk, 20);
        const response = await this.rpc("file.write", payload, { timeout: 8e3, signal });
        if (response.writtenBytes !== offset + chunk.length) throw new Error("Incomplete binary file transfer acknowledgement");
        onProgress?.({ writtenBytes: offset + chunk.length, totalBytes: bytes.length });
      }
      const result = await this.rpc("file.write", { action: "commit", uploadId: begin.uploadId }, { timeout: 8e3, signal });
      if (result.complete !== true || result.bytes !== bytes.length) throw new Error("Incomplete binary file commit acknowledgement");
      committed = true;
      if (bytes.length === 0) onProgress?.({ writtenBytes: 0, totalBytes: 0 });
      if (runAfterWrite) await this.rpc("script.run", { path }, { timeout: 8e3, signal });
      return { ...result, path, runAfterWrite };
    } finally {
      if (!committed) {
        await this.rpc("file.write", { action: "abort", uploadId }, { timeout: 1500 }).catch(() => {
        });
      }
    }
  }
  async writeScript(path, content, { runAfterWrite = false, signal = null } = {}) {
    return this.writeFile(path, content, { encoding: "utf-8", runAfterWrite, signal });
  }
  createOperationId() {
    return randomHex();
  }
  _networkOperationId(value) {
    const operationId = value ?? this.createOperationId();
    if (typeof operationId !== "string" || !/^[0-9a-f]{32}$/.test(operationId)) {
      throw new TypeError("Network operationId must be a 32-character lowercase hexadecimal string");
    }
    return operationId;
  }
  async networkStatus(options2 = {}) {
    if (!this.hasFeature("network.background")) {
      throw new Error("This firmware does not support background network management");
    }
    return this.rpc("device.control", { action: "network.status" }, options2);
  }
  async configureNetwork({ ssid, password, operationId = void 0 }, options2 = {}) {
    if (!this.hasFeature("network.configure")) {
      throw new Error("This firmware does not support network configuration");
    }
    if (typeof ssid !== "string" || typeof password !== "string") {
      throw new TypeError("Network name and password must be strings");
    }
    const { operationId: optionOperationId, ...rpcOptions } = options2;
    return this.rpc("device.control", {
      action: "network.configure",
      operationId: this._networkOperationId(operationId ?? optionOperationId),
      ssid,
      password
    }, rpcOptions);
  }
  async setNetworkEnabled(enabled, options2 = {}) {
    if (typeof enabled !== "boolean") throw new TypeError("Network enabled state must be a boolean");
    const { operationId, ...rpcOptions } = options2;
    return this.rpc("device.control", {
      action: "network.enable",
      operationId: this._networkOperationId(operationId),
      enabled
    }, rpcOptions);
  }
  async forgetNetwork(options2 = {}) {
    const { operationId, ...rpcOptions } = options2;
    return this.rpc("device.control", {
      action: "network.forget",
      operationId: this._networkOperationId(operationId)
    }, rpcOptions);
  }
  release({ timeout = 1200 } = {}) {
    if (this.releasePromise) return this.releasePromise;
    const negotiation = this.negotiatePromise;
    const operation = (async () => {
      if (negotiation) {
        try {
          await negotiation;
        } catch (_error) {
        }
      }
      if (!this.sessionId) return { ok: true, accepted: false };
      try {
        return await this.rpc("session.release", {}, { timeout, channel: "user.rpc" });
      } finally {
        this.close(new Error("EV-MUX session released"));
      }
    })();
    const tracked = operation.finally(() => {
      if (this.releasePromise === tracked) this.releasePromise = null;
    });
    this.releasePromise = tracked;
    return tracked;
  }
  async executePython(source, { timeout = null, signal = null } = {}) {
    if (timeout !== null && (!Number.isFinite(timeout) || timeout <= 0)) {
      throw new RangeError("Python execution timeout must be positive or null");
    }
    if (signal?.aborted) throw abortError(signal);
    const operation = createOperationDeadline(signal, timeout);
    signal = operation.signal;
    try {
      if (signal?.aborted) throw abortError(signal);
      const commandBytes = this.repl.execInputBytes ? this.repl.execInputBytes(source) : new TextEncoder().encode(`exec(${JSON.stringify(source)})\r
`).length;
      const inputLimit = this.repl.inputMaxBytes || 511;
      if (commandBytes <= inputLimit) {
        const result = await this.runScript(null, source, {
          timeout: null,
          signal,
          inlineSource: true
        });
        return result.output;
      }
      if (!this.hasFeature("file.write.binary") || !this.hasFeature("script.run")) {
        throw new Error(
          `Python source requires ${commandBytes} REPL bytes, above the firmware limit ${inputLimit}; upgrade firmware with file.write.binary and script.run support.`
        );
      }
      const path = `/.__espvision_exec_${Date.now().toString(36)}_${this.sequence}.py`;
      let primaryError = null;
      let cleanupError = null;
      let output = null;
      this._diagnostic("python.execute.chunked", { path, sourceBytes: new TextEncoder().encode(source).length, commandBytes });
      try {
        const result = await this.runScript(path, source, {
          timeout: null,
          signal,
          inlineCompletion: true
        });
        output = result.output;
      } catch (error2) {
        primaryError = error2;
      } finally {
        if (primaryError) await this.stopForRepl().catch(() => false);
        try {
          await this.repl.removeFile(path);
        } catch (error2) {
          cleanupError = error2;
          this._diagnostic("python.execute.cleanup_failed", { path, error: error2.message });
        }
      }
      if (primaryError) throw primaryError;
      if (cleanupError) throw cleanupError;
      return output;
    } finally {
      operation.dispose();
    }
  }
  async interrupt() {
    if (this.hasFeature("device.control")) {
      return this.rpc("device.control", { action: "stop" }, { timeout: 3e3 });
    }
    await this.writeFrame("repl.signal", "signal", null, new Uint8Array([3]));
    return { ok: true };
  }
  async control(operation, { timeout = 15e3, signal = null } = {}) {
    if (operation === "stop") return this.interrupt();
    if (signal?.aborted) throw abortError(signal);
    if (operation === "hard-reset" && this.hasFeature("device.control")) {
      return this.rpc("device.control", { action: "reset" }, { timeout, signal });
    }
    const command = {
      "soft-reset": "import machine; machine.soft_reset()\r\n",
      "hard-reset": "import machine; machine.reset()\r\n",
      bootloader: "import machine; machine.bootloader()\r\n"
    }[operation];
    if (!command) throw new Error(`Unsupported device control operation: ${operation}`);
    if (operation === "soft-reset") return this._softReset(command, { timeout, signal });
    await this.writeFrame("repl.signal", "signal", null, new Uint8Array([3]), { signal });
    await this.writeFrame("repl.stdin", "data", null, command, { signal });
    await awaitWithSignal(this.sleep(100), signal);
    return { ok: true, operation, acknowledged: false };
  }
  async _softReset(command, { timeout, signal }) {
    if (!Number.isFinite(timeout) || timeout <= 0) {
      throw new RangeError("VM reset timeout must be a positive number");
    }
    const controller = new AbortController();
    const abortFromCaller = () => controller.abort(abortError(signal));
    signal?.addEventListener("abort", abortFromCaller, { once: true });
    const timeoutError = Object.assign(new Error("VM did not become ready after soft reset"), {
      code: "VM_RESET_TIMEOUT"
    });
    const deadline = Date.now() + timeout;
    const timer = setTimeout(() => controller.abort(timeoutError), timeout);
    const resetSignal = controller.signal;
    const previousEpoch = this.vmEpoch;
    const owner = this.sessionId;
    try {
      if (signal?.aborted) abortFromCaller();
      const writeOptions = { signal: resetSignal, writeTimeout: timeout };
      await this.writeFrame("repl.signal", "signal", null, new Uint8Array([3]), writeOptions);
      await this.writeFrame("repl.stdin", "data", null, command, {
        signal: resetSignal,
        writeTimeout: Math.max(1, deadline - Date.now())
      });
      this._setVmReady(false);
      while (Date.now() < deadline) {
        if (resetSignal.aborted) throw abortError(resetSignal);
        if (this.sessionId !== owner || this.state === "disconnected") {
          throw Object.assign(new Error("Session lost while waiting for VM reset"), { code: "SESSION_REQUIRED" });
        }
        const response = await this.rpc("session.keepalive", {}, {
          timeout: Math.min(3e3, deadline - Date.now()),
          signal: resetSignal
        });
        if (isVmEpochNewer(response.vmEpoch, previousEpoch)) {
          this._updateVmEpoch(response.vmEpoch);
          if (response.vmEpoch === this.vmEpoch) this._setVmReady(response.vmReady);
        }
        if (isVmEpochNewer(this.vmEpoch, previousEpoch) && this.vmReady) {
          const probeEpoch = this.vmEpoch;
          if (await this.stopForRepl({ timeout: deadline - Date.now(), signal: resetSignal }) && Date.now() < deadline && !resetSignal.aborted && this.sessionId === owner && this.vmEpoch === probeEpoch && this.vmReady) {
            return { ok: true, operation: "soft-reset", acknowledged: true, vmEpoch: this.vmEpoch, vmReady: true };
          }
        }
        await awaitWithSignal(this.sleep(Math.min(100, Math.max(0, deadline - Date.now()))), resetSignal);
      }
      throw timeoutError;
    } catch (error2) {
      if (resetSignal.aborted) throw abortError(resetSignal);
      if (Date.now() >= deadline) throw timeoutError;
      throw error2;
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abortFromCaller);
    }
  }
  async stopForRepl({ timeout = 5e3, signal = null } = {}) {
    const deadline = Date.now() + timeout;
    for (let attempt = 0; attempt < 2 && Date.now() < deadline; attempt += 1) {
      if (signal?.aborted) throw abortError(signal);
      await this.writeFrame("repl.signal", "signal", null, new Uint8Array([3]), {
        signal,
        writeTimeout: Math.max(1, deadline - Date.now())
      });
      const remaining = Math.min(2500, deadline - Date.now());
      if (remaining <= 0) return false;
      try {
        await awaitWithSignal(this.repl.execPy("1", { timeout: remaining, signal }), signal);
        return true;
      } catch (error2) {
        if (signal?.aborted) throw abortError(signal);
      }
    }
    return false;
  }
  async runScript(path, content, options2 = {}) {
    const timeout = options2.timeout === void 0 ? 1e4 : options2.timeout;
    if (timeout !== null && (!Number.isFinite(timeout) || timeout <= 0)) {
      throw new RangeError("Script timeout must be a positive number or null for an interactive run");
    }
    const timeoutError = Object.assign(new Error(`script run timeout after ${timeout}ms`), { code: "SCRIPT_TIMEOUT" });
    const operation = createOperationDeadline(options2.signal ?? null, timeout, timeoutError);
    try {
      return await this._runScript(path, content, {
        ...options2,
        timeout: null,
        signal: operation.signal
      });
    } finally {
      operation.dispose();
    }
  }
  async _runScript(path, content, {
    timeout = 1e4,
    signal = null,
    onStarted = null,
    maxOutputChars = Number.POSITIVE_INFINITY,
    trial = null,
    inlineCompletion = false,
    inlineSource = false
  } = {}) {
    if (signal?.aborted) throw abortError(signal);
    if (inlineSource) {
      if (path !== null || typeof content !== "string" || inlineCompletion || trial) {
        throw new TypeError("Inline Python source must run without a device path or typed trial");
      }
    } else {
      validateRpcPath(path);
    }
    if (inlineCompletion && trial) throw new Error("Typed trial execution cannot use an inline runner");
    if (timeout !== null && (!Number.isFinite(timeout) || timeout <= 0)) {
      throw new RangeError("Script timeout must be a positive number or null for an interactive run");
    }
    if (!inlineSource && (content !== void 0 && !this.hasFeature("file.write.binary") || !this.hasFeature("script.run"))) {
      throw new Error("Running scripts requires script.run and uploading source also requires file.write.binary");
    }
    if (this.runCapture || this.runStarting) {
      throw new Error("A script is already running");
    }
    if (trial !== null && (!trial || typeof trial !== "object" || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(trial.operation_id ?? "") || typeof trial.source_path !== "string" || utf8Bytes(trial.source_path).length > 512 || !/^[a-f0-9]{64}$/.test(trial.source_hash ?? ""))) {
      throw new Error("Trial runner identity is invalid");
    }
    if (trial !== null && (!this.hasFeature("launcher.trial.status.v1") || !this.hasFeature("launcher.typed-runner.v1"))) {
      const error2 = new Error("Typed trial execution requires launcher.trial.status.v1 and launcher.typed-runner.v1 firmware features");
      error2.code = "UNSUPPORTED_OPERATION";
      throw error2;
    }
    this.runStarting = true;
    let inlineSourceVariable = null;
    let inlineSourcePrepared = false;
    try {
      if (!await this.stopForRepl({ timeout: timeout === null ? 5e3 : Math.min(timeout, 5e3), signal })) {
        throw new Error("could not stop the running script (no REPL answer after Ctrl-C)");
      }
      if (inlineSource) {
        inlineSourceVariable = `__evcore_python_${Date.now().toString(36)}_${++this.sequence}`;
        const assignments = this.repl.createInlineSourceAssignments(content, inlineSourceVariable);
        for (const assignment of assignments) {
          inlineSourcePrepared = true;
          await this.repl.execPy(assignment, { timeout: INLINE_PYTHON_REPL_TIMEOUT_MS, signal });
        }
      } else if (content !== void 0) {
        await this.writeScript(path, content, { signal });
      }
    } catch (error2) {
      if (inlineSourcePrepared) {
        await this.repl.execPy(`del ${inlineSourceVariable}`, { timeout: 3e3 }).catch(() => {
        });
      }
      throw error2;
    } finally {
      this.runStarting = false;
    }
    const completion = new Promise((resolve2, reject) => {
      const timer = timeout === null ? null : setTimeout(() => {
        const capture = this.runCapture;
        this.runCapture = null;
        cleanup();
        this.interrupt().catch(() => {
        });
        const error2 = new Error(`script run timeout after ${timeout}ms${capture?.output ? `
${capture.output}` : ""}`);
        error2.code = "SCRIPT_TIMEOUT";
        reject(error2);
      }, timeout);
      const onAbort = () => {
        const error2 = abortError(signal);
        this.runCapture = null;
        clearTimeout(timer);
        cleanup();
        this.interrupt().catch(() => {
        });
        reject(error2);
      };
      signal?.addEventListener("abort", onAbort, { once: true });
      const cleanup = () => signal?.removeEventListener("abort", onAbort);
      this.runCapture = {
        path,
        output: "",
        outputTruncated: false,
        maxOutputChars,
        resolve: (value) => {
          cleanup();
          resolve2(value);
        },
        reject: (error2) => {
          cleanup();
          reject(error2);
        },
        timer
      };
    });
    completion.catch(() => {
    });
    try {
      if (inlineSource) {
        const command = this.repl.createInlineScriptRunCommand(inlineSourceVariable);
        await this.repl.writeStdin(command, { signal });
      } else if (inlineCompletion) {
        const command = this.repl.createScriptRunCommand(path, { acknowledgeStart: Boolean(onStarted) });
        if (this.repl.scriptRunPrelude) await this.repl.execPy(this.repl.scriptRunPrelude, { timeout: timeout === null ? 5e3 : timeout, signal });
        const startAcknowledgement = onStarted ? this.repl.waitForScriptStart({ timeout: SCRIPT_START_ACK_TIMEOUT_MS, signal }) : null;
        startAcknowledgement?.catch(() => {
        });
        await this.repl.writeStdin(command, { signal });
        if (startAcknowledgement) await startAcknowledgement;
      } else {
        const sentinelLine = this.repl.createScriptEndSentinel();
        const request = { path };
        if (trial) {
          request.trial_operation_id = trial.operation_id;
          request.trial_source_path = trial.source_path;
          request.trial_source_hash = trial.source_hash;
        }
        await this.rpc("script.run", request, { timeout: 4e3, signal });
        await this.repl.writeStdin(sentinelLine, { signal });
      }
      await onStarted?.({ path, trial: trial ? structuredClone(trial) : null });
      return await completion;
    } catch (err) {
      const capture = this.runCapture;
      this.runCapture = null;
      clearTimeout(capture?.timer);
      this.repl.cancelScriptEndSentinel(err);
      capture?.reject(err);
      try {
        await completion;
      } catch (_err) {
      }
      throw err;
    }
  }
  async startScript(path, content, { onStarted = null, ...options2 } = {}) {
    let resolveStarted;
    let rejectStarted;
    let didStart = false;
    const started = new Promise((resolve2, reject) => {
      resolveStarted = resolve2;
      rejectStarted = reject;
    });
    const done = this.runScript(path, content, {
      timeout: null,
      maxOutputChars: 0,
      ...options2,
      onStarted: async (info) => {
        await onStarted?.(info);
        didStart = true;
        resolveStarted(info);
      }
    });
    done.catch((error2) => {
      if (!didStart) rejectStarted(error2);
    });
    return { ...await started, done };
  }
  scriptRunSnapshot() {
    if (!this.runCapture) return null;
    return {
      path: this.runCapture.path,
      output: this.runCapture.output.replace(/\r/g, ""),
      outputTruncated: this.runCapture.outputTruncated
    };
  }
  snapshot() {
    return {
      state: this.state,
      role: this.role,
      capabilities: this.capabilities,
      parser: this.parser.getDiagnostics?.(),
      transport: this.transport.getDiagnostics?.(),
      pendingRpc: this.pendingRpc.size,
      scriptRunning: Boolean(this.runCapture)
    };
  }
  close(error2 = new Error("connection closed")) {
    this.negotiateController?.abort(error2);
    this.draining = false;
    clearTimeout(this.keepaliveTimer);
    this.keepaliveTimer = null;
    this.keepaliveGeneration += 1;
    this.sessionGeneration += 1;
    this.state = "disconnected";
    this.capabilities = null;
    this.sessionId = null;
    this.vmEpoch = null;
    this.vmReady = false;
    this.vmReadyKnown = false;
    this.vmReadinessProbeActive = false;
    this.parser.active = false;
    for (const pending of this.pendingRpc.values()) {
      pending.reject(error2);
    }
    this.pendingRpc.clear();
    if (this.runCapture) {
      clearTimeout(this.runCapture.timer);
      this.runCapture.reject(error2);
      this.runCapture = null;
    }
    this.repl.failAll(error2);
  }
};

// node_modules/@esp-vision/device-core/src/evmux.js
var SOF = 30;
var EOF_GUARD = 31;
var HEADER_RE = /^EVMUX\/1 h=(\d+) p=(\d+) c=([0-9A-Fa-f]{8})\r\n$/;
var MAX_BUFFER = 1024 * 1024;
var MAX_HEADER = 96;
var crc32Table = null;
function crc32(bytes) {
  if (!crc32Table) {
    crc32Table = new Uint32Array(256);
    for (let i = 0; i < 256; i++) {
      let c = i;
      for (let j = 0; j < 8; j++) {
        c = c & 1 ? 3988292384 ^ c >>> 1 : c >>> 1;
      }
      crc32Table[i] = c >>> 0;
    }
  }
  let crc = 4294967295;
  for (const byte of bytes) {
    crc = crc32Table[(crc ^ byte) & 255] ^ crc >>> 8;
  }
  return (crc ^ 4294967295) >>> 0;
}
function concatBytes(a, b) {
  if (!a || a.length === 0) {
    return b;
  }
  if (!b || b.length === 0) {
    return a;
  }
  const out = new Uint8Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
}
function bytesToBase64(bytes) {
  let binary = "";
  const chunkSize = 32768;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}
function indexOfByte(bytes, value, from = 0) {
  for (let i = from; i < bytes.length; i++) {
    if (bytes[i] === value) {
      return i;
    }
  }
  return -1;
}
function findHeaderEnd(bytes) {
  for (let i = 1; i < bytes.length; i++) {
    if (bytes[i - 1] === 13 && bytes[i] === 10) {
      return i + 1;
    }
    if (i > MAX_HEADER) {
      return -2;
    }
  }
  return -1;
}
function appendLine(value) {
  if (!value.endsWith("\n")) {
    return value + "\n";
  }
  return value;
}
function decodePayloadText(payload) {
  return new TextDecoder("utf-8", { fatal: false }).decode(payload);
}
var EvMuxParser = class {
  constructor(handlers = {}) {
    this.handlers = handlers;
    this.buffer = new Uint8Array(0);
    this.rawTextDecoder = new TextDecoder("utf-8", { fatal: false });
    this.replTextDecoders = {
      "repl.stdout": new TextDecoder("utf-8", { fatal: false }),
      "repl.stderr": new TextDecoder("utf-8", { fatal: false })
    };
    this.metadataDecoder = new TextDecoder("utf-8", { fatal: false });
    this.active = false;
    this.rxBytes = 0;
    this.rxChunks = 0;
    this.frames = 0;
    this.droppedFrames = 0;
    this.lastChannel = null;
    this.maxMetadataLength = 65535;
    this.maxPayloadLength = MAX_BUFFER;
    this.frameProgressTimeoutMs = 12e3;
    this.frameTotalTimeoutMs = 12e3;
    this.partialFrame = null;
    this.partialFrameTimer = null;
  }
  setLimits({ metadataMax, payloadMax, frameProgressTimeoutMs, frameTotalTimeoutMs } = {}) {
    if (Number.isSafeInteger(metadataMax) && metadataMax > 0) this.maxMetadataLength = metadataMax;
    if (Number.isSafeInteger(payloadMax) && payloadMax > 0) this.maxPayloadLength = payloadMax;
    if (Number.isSafeInteger(frameProgressTimeoutMs) && frameProgressTimeoutMs > 0) {
      this.frameProgressTimeoutMs = frameProgressTimeoutMs;
    }
    if (Number.isSafeInteger(frameTotalTimeoutMs) && frameTotalTimeoutMs > 0) {
      this.frameTotalTimeoutMs = frameTotalTimeoutMs;
    }
  }
  resetReplTextDecoders() {
    this.replTextDecoders = {
      "repl.stdout": new TextDecoder("utf-8", { fatal: false }),
      "repl.stderr": new TextDecoder("utf-8", { fatal: false })
    };
  }
  _clearPartialFrame() {
    clearTimeout(this.partialFrameTimer);
    this.partialFrameTimer = null;
    this.partialFrame = null;
  }
  _armPartialFrameTimeout(progress = false) {
    const now = Date.now();
    if (!this.partialFrame) this.partialFrame = { startedAt: now, lastProgressAt: now };
    else if (progress) this.partialFrame.lastProgressAt = now;
    clearTimeout(this.partialFrameTimer);
    const remaining = Math.max(1, Math.min(
      this.frameProgressTimeoutMs - (now - this.partialFrame.lastProgressAt),
      this.frameTotalTimeoutMs - (now - this.partialFrame.startedAt)
    ));
    this.partialFrameTimer = setTimeout(() => {
      const expiredAt = Date.now();
      if (!this.partialFrame) return;
      if (expiredAt - this.partialFrame.lastProgressAt < this.frameProgressTimeoutMs && expiredAt - this.partialFrame.startedAt < this.frameTotalTimeoutMs) {
        this._armPartialFrameTimeout();
        return;
      }
      this._clearPartialFrame();
      this.buffer = new Uint8Array(0);
      this.rawTextDecoder = new TextDecoder("utf-8", { fatal: false });
      this.replTextDecoders = {
        "repl.stdout": new TextDecoder("utf-8", { fatal: false }),
        "repl.stderr": new TextDecoder("utf-8", { fatal: false })
      };
      this.droppedFrames += 1;
      this.handlers.other?.("[evmux] dropped an incomplete frame after receive timeout\n");
    }, remaining);
    this.partialFrameTimer.unref?.();
  }
  reset() {
    this._clearPartialFrame();
    this.buffer = new Uint8Array(0);
    this.rawTextDecoder = new TextDecoder("utf-8", { fatal: false });
    this.replTextDecoders = {
      "repl.stdout": new TextDecoder("utf-8", { fatal: false }),
      "repl.stderr": new TextDecoder("utf-8", { fatal: false })
    };
    this.metadataDecoder = new TextDecoder("utf-8", { fatal: false });
    this.active = false;
    this.rxBytes = 0;
    this.rxChunks = 0;
    this.frames = 0;
    this.droppedFrames = 0;
    this.lastChannel = null;
  }
  getDiagnostics() {
    return {
      active: this.active,
      rxBytes: this.rxBytes,
      rxChunks: this.rxChunks,
      bufferedBytes: this.buffer.length,
      frames: this.frames,
      droppedFrames: this.droppedFrames,
      lastChannel: this.lastChannel
    };
  }
  hasPartialFrame() {
    if (!this.partialFrame) return false;
    const text = this.metadataDecoder.decode(this.buffer);
    const tokens = ["EVMUX/1 h=", /^\d+/, " p=", /^\d+/, " c=", /^[0-9a-fA-F]{8}/, "\r\n"];
    let tail = text;
    for (const token of tokens) {
      if (typeof token === "string") {
        if (tail.length < token.length) return token.startsWith(tail);
        if (!tail.startsWith(token)) return false;
        tail = tail.slice(token.length);
      } else {
        if (!tail) return true;
        if (token.source.includes("{8}") && /^[0-9a-fA-F]{1,7}$/.test(tail)) return true;
        const match = token.exec(tail);
        if (!match) return false;
        tail = tail.slice(match[0].length);
      }
    }
    return true;
  }
  feedText(text) {
    if (text) {
      this.handlers.rawText?.(text);
    }
  }
  feedBytes(bytes) {
    const hadPartial = Boolean(this.partialFrame);
    this.rxBytes += bytes.length;
    this.rxChunks += 1;
    this.buffer = concatBytes(this.buffer, bytes);
    if (this.buffer.length > MAX_BUFFER) {
      const keepFrom = Math.max(0, this.buffer.length - MAX_BUFFER / 2);
      this.feedText(this.rawTextDecoder.decode(this.buffer.subarray(0, keepFrom), { stream: true }));
      this.buffer = this.buffer.subarray(keepFrom);
    }
    for (; ; ) {
      const sof = indexOfByte(this.buffer, SOF);
      if (sof < 0) {
        this.feedText(this.rawTextDecoder.decode(this.buffer, { stream: true }));
        this.buffer = new Uint8Array(0);
        return;
      }
      if (sof > 0) {
        this.feedText(this.rawTextDecoder.decode(this.buffer.subarray(0, sof), { stream: true }));
        this.buffer = this.buffer.subarray(sof);
      }
      const headerEnd = findHeaderEnd(this.buffer);
      if (headerEnd === -1) {
        this._armPartialFrameTimeout(hadPartial);
        return;
      }
      if (headerEnd === -2) {
        this.feedText(this.rawTextDecoder.decode(this.buffer.subarray(0, 1), { stream: true }));
        this.buffer = this.buffer.subarray(1);
        continue;
      }
      const header = this.metadataDecoder.decode(this.buffer.subarray(1, headerEnd));
      const match = HEADER_RE.exec(header);
      if (!match) {
        this.feedText(this.rawTextDecoder.decode(this.buffer.subarray(0, 1), { stream: true }));
        this.buffer = this.buffer.subarray(1);
        continue;
      }
      const metadataLen = Number(match[1]);
      const payloadLen = Number(match[2]);
      const expectedCrc = parseInt(match[3], 16) >>> 0;
      if (!Number.isFinite(metadataLen) || !Number.isFinite(payloadLen) || metadataLen <= 0 || payloadLen < 0 || metadataLen > this.maxMetadataLength || payloadLen > this.maxPayloadLength) {
        this._clearPartialFrame();
        this.feedText(this.rawTextDecoder.decode(this.buffer.subarray(0, 1), { stream: true }));
        this.buffer = this.buffer.subarray(1);
        continue;
      }
      const metadataStart = headerEnd;
      const payloadStart = metadataStart + metadataLen;
      const eofPos = payloadStart + payloadLen;
      const frameEnd = eofPos + 1;
      if (this.buffer.length < frameEnd) {
        this._armPartialFrameTimeout(hadPartial);
        return;
      }
      this._clearPartialFrame();
      if (this.buffer[eofPos] !== EOF_GUARD) {
        const nextSof = indexOfByte(this.buffer, SOF, 1);
        if (nextSof > 0) {
          this.buffer = this.buffer.subarray(nextSof);
        } else {
          this.buffer = new Uint8Array(0);
        }
        this.handlers.other?.("[evmux] dropped frame without EOF guard\n");
        this.droppedFrames += 1;
        continue;
      }
      let metadata;
      try {
        metadata = JSON.parse(this.metadataDecoder.decode(this.buffer.subarray(metadataStart, payloadStart)));
        if (!metadata || typeof metadata !== "object" || Array.isArray(metadata)) {
          throw new Error("metadata must be an object");
        }
      } catch (_err) {
        this.handlers.other?.("[evmux] dropped frame with invalid metadata\n");
        this.droppedFrames += 1;
        this.buffer = this.buffer.subarray(frameEnd);
        continue;
      }
      const payload = this.buffer.subarray(payloadStart, eofPos);
      this.buffer = this.buffer.subarray(frameEnd);
      if (expectedCrc !== 0 && crc32(payload) !== expectedCrc) {
        this.handlers.other?.("[evmux] dropped frame with invalid CRC\n");
        this.droppedFrames += 1;
        continue;
      }
      if (this.handlers.filterFrame?.(metadata, payload) === false) {
        this.droppedFrames += 1;
        this.handlers.frameRejected?.(metadata);
        continue;
      }
      this.frames += 1;
      this.lastChannel = metadata.channel || "unknown";
      this.dispatch(metadata, payload);
    }
  }
  dispatch(metadata, payload) {
    const channel = metadata.channel || "unknown";
    if (channel === "repl.stdout" || channel === "repl.stderr") {
      this.handlers.text?.(this.replTextDecoders[channel].decode(payload, { stream: true }));
      return;
    }
    if (channel === "log.idf") {
      const text = decodePayloadText(payload);
      const prefix = metadata.method ? `[${metadata.method}] ` : "";
      this.handlers.log?.(appendLine(prefix + text));
      return;
    }
    if (channel === "user.rpc" || channel === "debug.rpc") {
      if (channel === "debug.rpc" && metadata.type === "rsp" && metadata.contentType === "image/jpeg") {
        this.handlers.debugImage?.(bytesToBase64(payload), {
          width: Number(metadata.width) || 0,
          height: Number(metadata.height) || 0,
          size: payload.length,
          format: "jpg",
          encoding: "binary",
          route: metadata.route || "",
          seq: metadata.seq
        }, payload, metadata);
        this.handlers.rpc?.(metadata, { ok: true, contentType: "image/jpeg", bytes: payload.length });
        return;
      }
      if (metadata.type !== "rsp" && metadata.type !== "event") {
        this.handlers.command?.(appendLine(`${channel} ${metadata.type || "frame"} ${metadata.method || ""} #${metadata.seq ?? "-"}`));
        return;
      }
      const text = decodePayloadText(payload);
      let logFrame = true;
      try {
        logFrame = this.handlers.rpc?.(metadata, JSON.parse(text)) !== false;
      } catch (_err) {
        logFrame = this.handlers.rpc?.(metadata, null) !== false;
      }
      if (!logFrame) {
        return;
      }
      const line = `${metadata.type || "frame"} ${metadata.method || ""} #${metadata.seq ?? "-"} ${text}`;
      this.handlers.command?.(appendLine(`${channel} ${line}`));
      return;
    }
    if (channel === "preview.frame" && metadata.contentType === "image/jpeg") {
      this.handlers.preview?.(bytesToBase64(payload), {
        width: Number(metadata.width) || 0,
        height: Number(metadata.height) || 0,
        size: payload.length,
        format: "jpg",
        encoding: "binary",
        route: metadata.route || "",
        seq: metadata.seq
      }, payload);
      return;
    }
    this.handlers.other?.(appendLine(`${channel} ${payload.length} bytes`));
  }
};
function makeEvMuxFrame({ channel, type = "data", method = null, payload = "", seq = 0, sid = "web-ide", sessionId = void 0, vmEpoch = void 0, contentType = void 0, width = void 0, height = void 0, route = void 0, encoding = void 0 }) {
  const payloadBytes2 = payload instanceof Uint8Array ? payload : new TextEncoder().encode(payload);
  const metadata = {
    sid,
    seq,
    channel,
    type,
    encoding: encoding ?? (channel.endsWith(".rpc") ? "json" : "text"),
    ...sessionId ? { sessionId } : {},
    ...vmEpoch !== void 0 ? { vmEpoch } : {},
    ...contentType ? { contentType } : {},
    ...Number.isFinite(width) ? { width } : {},
    ...Number.isFinite(height) ? { height } : {},
    ...route ? { route } : {}
  };
  if (method) {
    metadata.method = method;
  }
  const metadataBytes = new TextEncoder().encode(JSON.stringify(metadata));
  const checksum = encoding === "binary" ? crc32(payloadBytes2).toString(16).padStart(8, "0") : "00000000";
  const header = new TextEncoder().encode(`EVMUX/1 h=${metadataBytes.length} p=${payloadBytes2.length} c=${checksum}\r
`);
  const out = new Uint8Array(header.length + metadataBytes.length + payloadBytes2.length + 1);
  out.set(header, 0);
  out.set(metadataBytes, header.length);
  out.set(payloadBytes2, header.length + metadataBytes.length);
  out[out.length - 1] = EOF_GUARD;
  return out;
}

// node_modules/@esp-vision/device-core/src/evrepl.js
var PROMPT = ">>> ";
var EV_REPL_INPUT_MAX_BYTES = 511;
var EV_REPL_FILE_CHUNK_BYTES = 224;
function pythonString(value) {
  return JSON.stringify(String(value));
}
function escapeForExec(source) {
  return source.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r/g, "").replace(/\n/g, "\\n").replace(/[^\x20-\x7e]/gu, (char) => {
    const code = char.codePointAt(0);
    return code <= 65535 ? `\\u${code.toString(16).padStart(4, "0")}` : `\\U${code.toString(16).padStart(8, "0")}`;
  });
}
function evReplExecInputBytes(source) {
  const command = `exec("${escapeForExec(source)}")\r
`;
  return new TextEncoder().encode(command).length;
}
function abortReason(signal) {
  if (signal?.reason instanceof Error) {
    return signal.reason;
  }
  const error2 = new Error(signal?.reason ? String(signal.reason) : "REPL operation cancelled");
  error2.name = "AbortError";
  return error2;
}
function throwIfAborted(signal) {
  if (signal?.aborted) {
    throw abortReason(signal);
  }
}
var EvRepl = class {
  /**
   * @param {object} io
   * @param {(channel: string, type: string, method: string|null, payload: string|Uint8Array) => Promise<unknown>} io.writeEvmux
   */
  constructor(io) {
    this.writeEvmux = io.writeEvmux;
    this.buffer = "";
    this.waiters = [];
    this.onScriptEnd = null;
    this.scriptStartMarker = null;
    this.scriptStartSeen = false;
    this.scriptStartWaiter = null;
    this.scriptEndMarker = null;
    this.scriptEndCommand = null;
    this.scriptSentinelSeq = 0;
    this.scriptEndPromptOffset = null;
    this.execQueue = Promise.resolve();
    this.closedError = null;
    this.inputMaxBytes = EV_REPL_INPUT_MAX_BYTES;
  }
  execInputBytes(source) {
    return evReplExecInputBytes(source);
  }
  createScriptEndSentinel() {
    const randomId = globalThis.crypto?.randomUUID?.() || `${Date.now().toString(36)}-${++this.scriptSentinelSeq}`;
    this.scriptEndMarker = `~~EVSCRIPT-END:${randomId}~~`;
    this.scriptEndCommand = `print(${pythonString(this.scriptEndMarker)})`;
    return `${this.scriptEndCommand}\r
`;
  }
  createScriptStartSentinel() {
    const randomId = globalThis.crypto?.randomUUID?.() || `${Date.now().toString(36)}-${++this.scriptSentinelSeq}`;
    this.scriptStartMarker = `~~EVSCRIPT-START:${randomId}~~`;
    this.scriptStartSeen = false;
    return `print(${pythonString(this.scriptStartMarker)})`;
  }
  waitForScriptStart({ timeout = 5e3, signal = null } = {}) {
    if (!Number.isFinite(timeout) || timeout <= 0) {
      throw new RangeError("Script start acknowledgement timeout must be positive");
    }
    if (this.scriptStartSeen) {
      this.scriptStartSeen = false;
      return Promise.resolve();
    }
    if (!this.scriptStartMarker) {
      return Promise.reject(Object.assign(new Error("Script start acknowledgement is unavailable"), {
        code: "SCRIPT_START_MISSING"
      }));
    }
    if (signal?.aborted) {
      return Promise.reject(abortReason(signal));
    }
    if (this.scriptStartWaiter) return this.scriptStartWaiter.promise;
    let waiter;
    const promise = new Promise((resolve2, reject) => {
      const cleanup = () => {
        clearTimeout(waiter.timer);
        signal?.removeEventListener("abort", onAbort);
        if (this.scriptStartWaiter === waiter) this.scriptStartWaiter = null;
      };
      const settle = (callback, value) => {
        cleanup();
        callback(value);
      };
      const onAbort = () => settle(reject, abortReason(signal));
      waiter = {
        promise: null,
        resolve: () => {
          this.scriptStartSeen = false;
          settle(resolve2);
        },
        reject: (error2) => settle(reject, error2),
        timer: setTimeout(() => settle(reject, Object.assign(
          new Error(`script start acknowledgement timeout after ${timeout}ms`),
          { code: "SCRIPT_START_TIMEOUT" }
        )), timeout)
      };
      this.scriptStartWaiter = waiter;
      signal?.addEventListener("abort", onAbort, { once: true });
      if (signal?.aborted) onAbort();
    });
    waiter.promise = promise;
    return promise;
  }
  createScriptRunCommand(path, { acknowledgeStart = false } = {}) {
    const start = acknowledgeStart ? this.createScriptStartSentinel() : null;
    const end = this.createScriptEndSentinel().trim();
    const source = (target) => `try:
${start ? ` ${start}
` : ""} execfile(${target})
except BaseException as __evcore_error:
 __import__('sys').print_exception(__evcore_error)
finally:
 ${end}`;
    let command = `exec("${escapeForExec(source(pythonString(path)))}")\r
`;
    this.scriptRunPrelude = null;
    if (new TextEncoder().encode(command).length > this.inputMaxBytes) {
      this.scriptRunPrelude = `__evcore_script_path=${pythonString(path)}`;
      command = `exec("${escapeForExec(source("__evcore_script_path"))}")\r
`;
    }
    if (new TextEncoder().encode(command).length > this.inputMaxBytes || this.scriptRunPrelude && this.execInputBytes(this.scriptRunPrelude) > this.inputMaxBytes) {
      this.cancelScriptEndSentinel();
      throw new Error("Script runner command exceeds the REPL input limit");
    }
    this.scriptEndCommand = command.trimEnd();
    this.scriptRunEcho = true;
    return command;
  }
  createInlineSourceAssignments(source, variableName) {
    if (typeof source !== "string" || !/^__[A-Za-z0-9_]+$/.test(variableName)) {
      throw new TypeError("Inline Python source requires a string and a private variable name");
    }
    const characters = Array.from(source);
    const statements = [];
    let chunk = "";
    const statementFor = (value, first) => `${variableName}${first ? "=" : "+="}${JSON.stringify(value)}`;
    for (const character of characters) {
      const candidate = chunk + character;
      const candidateStatement = statementFor(candidate, statements.length === 0);
      if (this.execInputBytes(candidateStatement) <= this.inputMaxBytes) {
        chunk = candidate;
        continue;
      }
      if (!chunk) throw new Error("Inline Python source character exceeds the REPL input limit");
      statements.push(statementFor(chunk, statements.length === 0));
      chunk = character;
      if (this.execInputBytes(statementFor(chunk, false)) > this.inputMaxBytes) {
        throw new Error("Inline Python source character exceeds the REPL input limit");
      }
    }
    if (chunk || statements.length === 0) statements.push(statementFor(chunk, statements.length === 0));
    return statements;
  }
  createInlineScriptRunCommand(variableName) {
    if (!/^__[A-Za-z0-9_]+$/.test(variableName)) {
      throw new TypeError("Inline Python run requires a private variable name");
    }
    const end = this.createScriptEndSentinel().trim();
    const source = `try:
 exec(${variableName})
except BaseException as __evcore_error:
 __import__('sys').print_exception(__evcore_error)
finally:
 try:
  del ${variableName}
 except NameError:
  pass
 ${end}`;
    const command = `exec("${escapeForExec(source)}")\r
`;
    if (new TextEncoder().encode(command).length > this.inputMaxBytes) {
      this.cancelScriptEndSentinel();
      throw new Error("Inline Python runner exceeds the REPL input limit");
    }
    this.scriptEndCommand = command.trimEnd();
    this.scriptRunEcho = true;
    return command;
  }
  cancelScriptEndSentinel(error2 = null) {
    this.scriptStartMarker = null;
    this.scriptStartSeen = false;
    this.scriptStartWaiter?.reject(error2 || Object.assign(new Error("Script ended before its start acknowledgement"), {
      code: "SCRIPT_START_MISSING"
    }));
    this.scriptEndMarker = null;
    this.scriptEndCommand = null;
    this.scriptRunEcho = false;
    this.scriptRunPrelude = null;
    this.scriptEndPromptOffset = null;
  }
  /**
   * Swallow the current run's unique sentinel output line and fire
   * onScriptEnd. Its echoed print command is buffered and removed with it.
   */
  drainScriptEnd() {
    if (this.scriptRunEcho && this.scriptEndCommand) {
      const at = this.buffer.indexOf(this.scriptEndCommand);
      const end = at + this.scriptEndCommand.length;
      if (at >= 0 && this.buffer.slice(end, end + 2) === "\r\n") {
        this.buffer = this.buffer.slice(0, at) + this.buffer.slice(end + 2);
        this.scriptEndCommand = null;
        this.scriptRunEcho = false;
      }
    }
    this.drainScriptStart();
    const marker = this.scriptEndMarker;
    if (!marker) {
      return;
    }
    let searchFrom = 0;
    for (; ; ) {
      const at = this.buffer.indexOf(marker, searchFrom);
      if (at < 0) {
        return;
      }
      let end = at + marker.length;
      const tail = this.buffer[end];
      if (tail === void 0) {
        return;
      }
      if (tail !== "\r" && tail !== "\n") {
        searchFrom = end;
        continue;
      }
      if (tail === "\r") {
        if (end + 1 >= this.buffer.length) {
          return;
        }
        end += this.buffer[end + 1] === "\n" ? 2 : 1;
      } else {
        end += 1;
      }
      let before = this.buffer.slice(0, at);
      const echoAt = this.scriptEndCommand ? before.lastIndexOf(this.scriptEndCommand) : -1;
      if (echoAt >= 0) {
        let echoEnd = echoAt + this.scriptEndCommand.length;
        if (before.slice(echoEnd, echoEnd + 2) === "\r\n") {
          echoEnd += 2;
        } else if (before[echoEnd] === "\r" || before[echoEnd] === "\n") {
          echoEnd += 1;
        }
        before = before.slice(0, echoAt) + before.slice(echoEnd);
      }
      this.buffer = before + this.buffer.slice(end);
      this.cancelScriptEndSentinel();
      this.scriptEndPromptOffset = before.length;
      this.onScriptEnd?.();
      return;
    }
  }
  drainScriptStart() {
    const marker = this.scriptStartMarker;
    if (!marker) return;
    let searchFrom = 0;
    for (; ; ) {
      const at = this.buffer.indexOf(marker, searchFrom);
      if (at < 0) return;
      let end = at + marker.length;
      const tail = this.buffer[end];
      if (tail === void 0) return;
      if (tail !== "\r" && tail !== "\n") {
        searchFrom = end;
        continue;
      }
      if (tail === "\r") {
        if (end + 1 >= this.buffer.length) return;
        end += this.buffer[end + 1] === "\n" ? 2 : 1;
      } else {
        end += 1;
      }
      this.buffer = this.buffer.slice(0, at) + this.buffer.slice(end);
      this.scriptStartMarker = null;
      this.scriptStartSeen = true;
      this.scriptStartWaiter?.resolve();
      return;
    }
  }
  /**
   * Length of the buffer suffix that could grow into the sentinel marker
   * (starts with at least '~~'). Held back from passthrough so a marker
   * split across frames never leaks half into the terminal.
   */
  partialMarkerTail() {
    const marker = this.scriptEndMarker;
    if (!marker) {
      return 0;
    }
    const commandAt = this.scriptEndCommand ? this.buffer.lastIndexOf(this.scriptEndCommand) : -1;
    if (commandAt >= 0) {
      return this.buffer.length - commandAt;
    }
    for (const activeMarker of [this.scriptStartMarker, marker]) {
      if (activeMarker && this.buffer.endsWith(activeMarker + "\r")) {
        return activeMarker.length + 1;
      }
    }
    let hold = 0;
    for (const candidate of [this.scriptStartMarker, marker, this.scriptEndCommand]) {
      if (!candidate) {
        continue;
      }
      const max = Math.min(candidate.length, this.buffer.length);
      for (let len = max; len >= 1; len--) {
        if (this.buffer.endsWith(candidate.slice(0, len))) {
          hold = Math.max(hold, len);
          break;
        }
      }
    }
    return hold;
  }
  /**
   * Feed decoded repl.stdout text. Returns the part not consumed by an
   * internal exec — the caller writes only that part to the
   * terminal, so bootstrap and file-transfer traffic (device info, fs walk,
   * hex file reads) never shows up as garbage in the user's console.
   * Interactive typing is unaffected: it registers no waiters, so every
   * byte passes straight through.
   */
  feedStdout(text) {
    if (!text) {
      return "";
    }
    this.buffer += text;
    this.drainScriptEnd();
    let passthrough = "";
    let holdPromptTail = false;
    if (this.scriptEndPromptOffset !== null) {
      const prefix = this.buffer.slice(0, this.scriptEndPromptOffset);
      const tail = this.buffer.slice(this.scriptEndPromptOffset);
      if (tail.length < PROMPT.length && PROMPT.startsWith(tail)) {
        this.buffer = tail;
        this.scriptEndPromptOffset = 0;
        passthrough = prefix;
        holdPromptTail = true;
      } else if (tail.startsWith(PROMPT)) {
        this.buffer = prefix + tail.slice(PROMPT.length);
        this.scriptEndPromptOffset = null;
      } else {
        this.scriptEndPromptOffset = null;
      }
    }
    this.drain();
    if (this.waiters.length === 0) {
      const hold = holdPromptTail ? this.buffer.length : this.partialMarkerTail();
      const out = this.buffer.slice(0, this.buffer.length - hold);
      this.buffer = this.buffer.slice(this.buffer.length - hold);
      return passthrough + out;
    }
    return "";
  }
  drain() {
    for (let i = this.waiters.length - 1; i >= 0; i--) {
      const waiter = this.waiters[i];
      let start = 0;
      if (waiter.cmd) {
        const echoAt = this.buffer.indexOf(waiter.cmd);
        if (echoAt < 0) {
          continue;
        }
        start = echoAt + waiter.cmd.length;
      }
      const promptAt = this.buffer.indexOf(PROMPT, start);
      if (promptAt < 0) {
        continue;
      }
      const output = this.buffer.slice(waiter.cmd ? start : 0, promptAt);
      this.buffer = this.buffer.slice(promptAt + PROMPT.length);
      this.waiters.splice(i, 1);
      clearTimeout(waiter.timer);
      waiter.removeAbortListener?.();
      waiter.resolve(output);
    }
  }
  failAll(error2) {
    this.closedError = error2;
    for (const waiter of this.waiters.splice(0)) {
      clearTimeout(waiter.timer);
      waiter.removeAbortListener?.();
      waiter.reject(error2);
    }
    this.cancelScriptEndSentinel(error2);
    this.buffer = "";
  }
  resetEpoch(error2) {
    this.failAll(error2);
    this.closedError = null;
  }
  /**
   * Execute one REPL input (single line) and resolve with everything it
   * printed before the next prompt, minus the echoed input line.
   */
  enqueue(operation, { signal = null } = {}) {
    const result = this.execQueue.then(() => {
      if (this.closedError) {
        throw this.closedError;
      }
      throwIfAborted(signal);
      return operation();
    });
    this.execQueue = result.catch(() => {
    });
    return result;
  }
  writeStdin(data, { signal = null } = {}) {
    return this.enqueue(async () => {
      const bytes = data instanceof Uint8Array ? data : new TextEncoder().encode(data);
      if (bytes.length <= this.inputMaxBytes) {
        return this.writeEvmux("repl.stdin", "data", null, data, { signal });
      }
      let result;
      for (let offset = 0; offset < bytes.length; offset += this.inputMaxBytes) {
        result = await this.writeEvmux(
          "repl.stdin",
          "data",
          null,
          bytes.subarray(offset, Math.min(offset + this.inputMaxBytes, bytes.length)),
          { signal }
        );
      }
      return result;
    }, { signal });
  }
  execLine(line, { timeout = 8e3, signal = null } = {}) {
    return this.enqueue(() => this._execLine(line, timeout, signal), { signal });
  }
  async _execLine(line, timeout, signal = null) {
    throwIfAborted(signal);
    const inputBytes = new TextEncoder().encode(`${line}\r
`).length;
    if (inputBytes > this.inputMaxBytes) {
      throw new Error(
        `Friendly-REPL input is ${inputBytes} bytes; firmware accepts at most ${this.inputMaxBytes}. Use chunked script execution.`
      );
    }
    let waiter;
    let commandWritten = false;
    const completion = new Promise((resolve2, reject) => {
      const removeWaiter = () => {
        const index = this.waiters.indexOf(waiter);
        if (index >= 0) {
          this.waiters.splice(index, 1);
        }
      };
      const fail2 = (error2) => {
        removeWaiter();
        clearTimeout(waiter.timer);
        waiter.removeAbortListener?.();
        reject(error2);
      };
      const timer = setTimeout(() => {
        fail2(Object.assign(new Error(`repl exec timeout: ${line.slice(0, 60)}`), { code: "TIMEOUT" }));
      }, timeout);
      const abort2 = () => {
        fail2(abortReason(signal));
        if (commandWritten) {
          void this.writeEvmux(
            "repl.signal",
            "signal",
            null,
            new Uint8Array([3])
          ).catch(() => {
          });
        }
      };
      waiter = {
        cmd: line,
        timer,
        resolve: resolve2,
        reject,
        removeAbortListener: signal ? () => signal.removeEventListener("abort", abort2) : null
      };
      this.waiters.push(waiter);
      if (signal) {
        signal.addEventListener("abort", abort2, { once: true });
        if (signal.aborted) abort2();
      }
    });
    completion.catch(() => {
    });
    if (signal?.aborted) return completion;
    try {
      await this.writeEvmux("repl.stdin", "data", null, line + "\r\n", { signal });
      commandWritten = true;
    } catch (err) {
      const index = this.waiters.indexOf(waiter);
      if (index >= 0) {
        this.waiters.splice(index, 1);
      }
      clearTimeout(waiter.timer);
      waiter.removeAbortListener?.();
      waiter.reject(err);
      try {
        await completion;
      } catch (_err) {
      }
      throw err;
    }
    const output = await completion;
    return output.replace(/\r/g, "");
  }
  /** Execute a (possibly multi-line) Python snippet via exec("..."). */
  execPy(source, { timeout = 8e3, signal = null } = {}) {
    return this.enqueue(() => this._execPy(source, timeout, signal), { signal });
  }
  _execPy(source, timeout = 8e3, signal = null) {
    return this._execLine(`exec("${escapeForExec(source)}")`, timeout, signal);
  }
  async getDeviceInfo({ signal = null } = {}) {
    const rsp = await this.execPy(`
import os,sys
try: u=os.uname()
except: u=('','','','',sys.platform)
try: v=sys.version.split(';')[1].strip()
except: v='MicroPython '+u[2]
mpy=getattr(sys.implementation, '_mpy', 0)
sp=':'.join(sys.path)
d=[u[4],u[2],u[0],v,mpy>>10,mpy&0xFF,(mpy>>8)&3,sp]
print('|'.join(str(x) for x in d))
`, { signal });
    const fields2 = rsp.trim().split("|");
    if (fields2.length < 8) {
      throw new Error(`unexpected device info response: ${rsp.trim().slice(0, 200)}`);
    }
    let [machine, release, sysname, version, mpy_arch, mpy_ver, mpy_sub, sys_path] = fields2;
    sys_path = sys_path.split(":");
    try {
      mpy_arch = [null, "x86", "x64", "armv6", "armv6m", "armv7m", "armv7em", "armv7emsp", "armv7emdp", "xtensa", "xtensawin", "rv32imc"][mpy_arch];
    } catch (_err) {
      mpy_arch = null;
    }
    mpy_ver = parseInt(mpy_ver, 10);
    mpy_sub = parseInt(mpy_sub, 10);
    if (!mpy_ver) {
      mpy_ver = "py";
    }
    return { machine, release, sysname, version, mpy_arch, mpy_ver, mpy_sub, sys_path };
  }
  async getFsStats(path = "/", { signal = null } = {}) {
    const pathLiteral = pythonString(path);
    const rsp = await this.execPy(`
import os
s = os.statvfs(${pathLiteral})
fs = s[1] * s[2]
ff = s[3] * s[0]
fu = fs - ff
print('%s|%s|%s'%(fu,ff,fs))
`, { signal });
    return rsp.trim().split("|");
  }
  /** List only the requested directory; recursion visits its descendants only. */
  async listFs(path, { recursive = false, signal = null } = {}) {
    const entries = [];
    const pending = [path];
    while (pending.length) {
      throwIfAborted(signal);
      const directory = pending.pop();
      const assignment = `p=${pythonString(directory)}.rstrip('/')`;
      const body = `
import os,json
try:
 r=[(n,os.stat(p+'/'+n)[0],os.stat(p+'/'+n)[6])for n in os.listdir(p or '/')]
except OSError as e:r=e.args[0]
print('__EVLIST__'+json.dumps(r))
`;
      let source = `${assignment}
${body}`;
      if (this.execInputBytes(source) > this.inputMaxBytes) {
        await this.execPy(assignment, { signal });
        source = body;
      }
      const response = await this.execPy(source, { signal });
      const line = response.trim().split("\n").findLast((value) => value.startsWith("__EVLIST__"));
      if (!line) throw Object.assign(new Error("Incomplete directory listing"), { code: "DEVICE_DIRECTORY_READ_INCOMPLETE" });
      const result = JSON.parse(line.slice("__EVLIST__".length));
      if (Number.isInteger(result)) {
        throw Object.assign(new Error(`Cannot list ${directory}: OSError ${result}`), {
          code: result === 2 ? "NOT_FOUND" : result === 20 ? "NOT_DIRECTORY" : "FILESYSTEM_ERROR",
          errno: result
        });
      }
      if (!Array.isArray(result)) throw new Error("Invalid directory listing");
      for (const item of result) {
        if (!Array.isArray(item) || item.length !== 3 || typeof item[0] !== "string" || !Number.isInteger(item[1]) || !Number.isSafeInteger(item[2]) || item[2] < 0 || item[0].includes("/") || [".", ".."].includes(item[0])) throw new Error("Invalid directory entry");
        const [name, mode, size] = item;
        const fullpath = `${directory === "/" ? "" : directory}/${name}`;
        const isDirectory = Boolean(mode & 16384);
        entries.push({ name, path: fullpath, type: isDirectory ? "directory" : "file", size: isDirectory ? 0 : size });
        if (recursive && isDirectory) pending.push(fullpath);
      }
    }
    return entries;
  }
  async walkFs({ signal = null } = {}) {
    const rsp = await this.execPy(`
import os
def walk(p):
 for n in os.listdir(p if p else '/'):
  fn=p+'/'+n
  try: s=os.stat(fn)
  except: s=(0,)*7
  try:
   if s[0] & 0x4000 == 0:
    print('f|'+fn+'|'+str(s[6]))
   elif n not in ('.','..'):
    print('d|'+fn+'|'+str(s[6]))
    walk(fn)
  except:
   print('f|'+p+'/???|'+str(s[6]))
walk('')
`, { timeout: 2e4, signal });
    const result = [];
    for (const line of rsp.split("\n")) {
      if (line === "") continue;
      let current = result;
      const [type, fullpath, size] = line.trim().split("|");
      const path = fullpath.split("/");
      let file;
      if (type == "f") {
        file = path.pop();
      }
      for (const segment of path) {
        if (segment === "") continue;
        const next = current.filter((x) => x.name === segment && "content" in x);
        if (next.length) {
          current = next[0].content;
        } else {
          const prev = current;
          current = [];
          prev.push({ name: segment, path: path.join("/"), content: current });
        }
      }
      if (type == "f") {
        current.push({ name: file, path: fullpath, size: parseInt(size, 10) });
      }
    }
    return result;
  }
  async readFile(fn, { timeout = null, chunkTimeout = 3e4, signal = null, maxBytes = null } = {}) {
    if (timeout !== null && (!Number.isFinite(timeout) || timeout <= 0)) {
      throw new RangeError("Device file read timeout must be positive or null");
    }
    if (!Number.isFinite(chunkTimeout) || chunkTimeout <= 0) {
      throw new RangeError("Device file read chunk timeout must be positive");
    }
    if (maxBytes !== null && (!Number.isSafeInteger(maxBytes) || maxBytes < 0 || maxBytes > 16 * 1024 * 1024)) {
      throw Object.assign(new Error("Invalid bounded file read limit"), { code: "DEVICE_READ_LIMIT_INVALID" });
    }
    return this.enqueue(async () => {
      const deadline = timeout === null ? null : Date.now() + timeout;
      const commandBudget = () => {
        if (deadline === null) return chunkTimeout;
        const remaining = deadline - Date.now();
        if (remaining <= 0) throw Object.assign(new Error("Device file read timeout"), { code: "TIMEOUT" });
        return Math.min(chunkTimeout, remaining);
      };
      const chunks = [];
      let offset = 0;
      let size = null;
      let filePath = pythonString(fn);
      const incomplete = () => Object.assign(new Error(`Incomplete file response for ${fn}`), { code: "DEVICE_FILE_READ_INCOMPLETE" });
      for (; ; ) {
        throwIfAborted(signal);
        const count = maxBytes === null ? 1024 : Math.min(1024, maxBytes - offset + 1);
        let source = `
import binascii
try:
 with open(${filePath},'rb') as f:
  f.seek(0,2)
  z=f.tell()
  f.seek(${offset})
  b=f.read(${count})
  print('__EVREAD_OK__%d:%d:'%(z,len(b))+binascii.hexlify(b).decode())
except Exception as e:
 print('__EVREAD_ERROR__'+repr(e))
`;
        if (this.execInputBytes(source) > this.inputMaxBytes) {
          await this._execPy(`__evcore_read_path=${pythonString(fn)}`, commandBudget(), signal);
          commandBudget();
          source = source.replace(filePath, "__evcore_read_path");
          filePath = "__evcore_read_path";
        }
        const rsp = await this._execPy(source, commandBudget(), signal);
        commandBudget();
        const errorAt = rsp.indexOf("__EVREAD_ERROR__");
        if (errorAt >= 0) throw new Error(`Unable to read ${fn}: ${rsp.slice(errorAt + 16).trim()}`);
        const match = /(?:^|\n)__EVREAD_OK__(\d+):(\d+):([0-9a-fA-F]*)\s*$/.exec(rsp);
        if (!match) throw incomplete();
        const reportedSize = Number(match[1]);
        const reportedCount = Number(match[2]);
        const hex = match[3];
        if (!Number.isSafeInteger(reportedSize) || !Number.isSafeInteger(reportedCount) || reportedCount > count || hex.length !== reportedCount * 2) throw incomplete();
        if (size !== null && size !== reportedSize) {
          throw Object.assign(new Error(`Device file changed during read: ${fn}`), { code: "DEVICE_FILE_CHANGED" });
        }
        size = reportedSize;
        const bytes = Uint8Array.from(hex.match(/../g) || [], (value) => parseInt(value, 16));
        offset += bytes.length;
        if (offset > size || !bytes.length && offset < size) throw incomplete();
        if (maxBytes !== null && size > maxBytes) {
          throw Object.assign(new Error("Device file exceeds the bounded read limit"), { code: "DEVICE_FILE_TOO_LARGE" });
        }
        chunks.push(bytes);
        if (offset === size) break;
      }
      const result = new Uint8Array(offset);
      let position = 0;
      for (const chunk of chunks) {
        result.set(chunk, position);
        position += chunk.length;
      }
      return result;
    }, { signal });
  }
  /**
   * Run one filesystem statement and raise on failure. The snippet prints a
   * JSON marker as its last line so errors (e.g. removing a non-empty
   * directory) surface as exceptions instead of silent REPL tracebacks.
   */
  async _fsOp(stmt, { signal = null, path = void 0 } = {}) {
    const source = (statement) => `
import os,json
try:
 ${statement}
 print(json.dumps({'ok':True}))
except OSError as e:
 print(json.dumps({'ok':False,'err':e.args[0] if e.args else -1}))
`;
    let rsp;
    if (path !== void 0 && this.execInputBytes(source(stmt)) > this.inputMaxBytes) {
      rsp = await this.enqueue(async () => {
        await this._execPy(`__evcore_fs_path=${pythonString(path)}`, 8e3, signal);
        return this._execPy(source(stmt.replace(pythonString(path), "__evcore_fs_path")), 8e3, signal);
      }, { signal });
    } else {
      rsp = await this.execPy(source(stmt), { signal });
    }
    const result = JSON.parse(rsp.trim().split("\n").pop());
    if (!result.ok) {
      if (result.err === 39) {
        throw new Error("Directory not empty");
      }
      throw new Error(`OSError ${result.err}`);
    }
  }
  async touchFile(fn) {
    await this._fsOp(`open(${pythonString(fn)},'wb').close()`);
  }
  async removeFile(path, { signal = null } = {}) {
    await this._fsOp(`os.remove(${pythonString(path)})`, { signal, path });
  }
  async removeDir(path, { signal = null } = {}) {
    await this._fsOp(`os.rmdir(${pythonString(path)})`, { signal, path });
  }
  async makePath(path) {
    const pathLiteral = pythonString(path);
    const rsp = await this.execPy(`
import os,json
try:
 p=''
 for d in ${pathLiteral}.split('/'):
  if not d: continue
  p += '/'+d
  try: os.mkdir(p)
  except OSError as e:
   if e.args[0] not in (17, 20): raise
 print(json.dumps({'ok':True}))
except OSError as e:
 print(json.dumps({'ok':False,'err':e.args[0] if e.args else -1}))
`);
    const result = JSON.parse(rsp.trim().split("\n").pop());
    if (!result.ok) {
      throw new Error(`OSError ${result.err}`);
    }
  }
  writeFile(fn, data, chunk_size = EV_REPL_FILE_CHUNK_BYTES, direct = false, { signal = null } = {}) {
    return this.enqueue(
      () => this._writeFile(fn, data, chunk_size, direct, signal),
      { signal }
    );
  }
  async _writeFile(fn, data, chunk_size, direct, signal = null) {
    throwIfAborted(signal);
    if (typeof data === "string" || data instanceof String) {
      data = new TextEncoder().encode(data);
    } else if (data instanceof ArrayBuffer) {
      data = new Uint8Array(data);
    }
    const dest = direct ? fn : ".viper.tmp";
    const destLiteral = pythonString(dest);
    const pathLiteral = pythonString(fn);
    await this._execPy(`
import os
try:
 import binascii
 u=binascii.unhexlify
except:
 u=lambda s: bytes(int(s[i:i+2], 16) for i in range(0, len(s), 2))
f=open(${destLiteral},'wb')
`, 8e3, signal);
    for (let i = 0; i < data.byteLength; i += chunk_size) {
      throwIfAborted(signal);
      const chunk = data.subarray(i, Math.min(i + chunk_size, data.byteLength));
      const hex = [...chunk].map((b) => b.toString(16).padStart(2, "0")).join("");
      await this._execPy(`f.write(u('${hex}'))`, 8e3, signal);
    }
    if (direct) {
      await this._execPy("f.close()", 8e3, signal);
    } else {
      await this._execPy(`f.close()
try: os.remove(${pathLiteral})
except: pass
os.rename(${destLiteral},${pathLiteral})
`, 8e3, signal);
    }
  }
  async readSysInfoMD() {
    return await this.execPy(`
import os,sys,gc
gc.collect()
mu = gc.mem_alloc()
mf = gc.mem_free()
ms = mu + mf
uname=os.uname()
p=print
def size_fmt(size):
 suffixes = ['B','KiB','MiB','GiB','TiB']
 i = 0
 while size > 1024 and i < len(suffixes)-1:
  i += 1
  size //= 1024
 return "%d%s" % (size, suffixes[i])
p('## Machine')
p('- Name: \`'+uname.machine+'\`')
try:
 gc.collect()
 import microcontroller as uc
 p('- CPU: \`%s @ %s MHz\`' % (sys.platform, uc.cpu.frequency // 1_000_000))
 p('- UID: \`%s\`' % (uc.cpu.uid.hex(),))
 p('- Temp.: \`%s \xB0C\`' % (uc.cpu.temperature,))
 p('- Voltage: \`%s V\`' % (uc.cpu.voltage,))
except:
 try:
  gc.collect()
  import machine
  p('- CPU: \`%s @ %s MHz\`' % (sys.platform, machine.freq() // 1_000_000))
 except:
  p('- CPU: \`'+sys.platform+'\`')
p()
p('## System')
p('- Version: \`'+sys.version.split(";")[1].strip()+'\`')
if ms:
 p('- Memory use:  \`%s / %s, free: %d%%\`' % (size_fmt(mu), size_fmt(ms), (mf * 100) // ms))
`);
  }
};

// node_modules/@esp-vision/device-core/src/network_discovery.js
var ESP_VISION_DISCOVERY_SERVICE = "_esp-vision._tcp.local";
function normalizeDiscoveredDevice(value) {
  if (!value || !/^[0-9a-f]{12}$/.test(value.deviceId)) throw new Error("Invalid discovered device identity");
  if (typeof value.hostname !== "string" || value.hostname.length > 63 || !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(value.hostname)) throw new Error("Invalid discovered hostname");
  if (typeof value.board !== "string" || !value.board || value.board.length > 96 || typeof value.firmwareVersion !== "string" || !value.firmwareVersion || value.firmwareVersion.length > 255 || !Number.isInteger(value.evMuxVersion) || !Number.isInteger(value.port) || value.port < 1 || value.port > 65535) throw new Error("Invalid discovery metadata");
  const addresses = [...new Set(value.addresses || [])].filter((address) => typeof address === "string" && address.split(".").length === 4 && address.split(".").every((part) => /^(0|[1-9][0-9]{0,2})$/.test(part) && Number(part) <= 255));
  if (!addresses.length) throw new Error("No discovered IPv4 address");
  return {
    deviceId: value.deviceId,
    hostname: value.hostname,
    board: value.board,
    firmwareVersion: value.firmwareVersion,
    evMuxVersion: value.evMuxVersion,
    compatible: value.evMuxVersion === 4,
    port: value.port,
    addresses,
    ...value.connectionUrl ? { connectionUrl: value.connectionUrl } : {},
    ...value.expiresAt ? { expiresAt: value.expiresAt } : {}
  };
}
var NetworkDiscovery = class {
  constructor(provider) {
    if (typeof provider?.list !== "function") throw new TypeError("Discovery provider.list is required");
    this.provider = provider;
  }
  async list({ timeout = 3e3, signal } = {}) {
    if (!Number.isInteger(timeout) || timeout < 50 || timeout > 1e4) throw new RangeError("Discovery timeout must be 50..10000 ms");
    signal?.throwIfAborted();
    const controller = new AbortController();
    const abort2 = () => controller.abort(signal.reason);
    signal?.addEventListener("abort", abort2, { once: true });
    const timer = setTimeout(() => controller.abort(new Error("Discovery provider timed out")), timeout + 1e3);
    let onAbort;
    try {
      const aborted2 = new Promise((_, reject) => {
        onAbort = () => reject(controller.signal.reason);
        controller.signal.addEventListener("abort", onAbort, { once: true });
      });
      const devices = await Promise.race([this.provider.list({ timeout, signal: controller.signal }), aborted2]);
      controller.signal.throwIfAborted();
      if (!Array.isArray(devices) || devices.length > 256) throw new Error("Invalid discovery response");
      return devices.map(normalizeDiscoveredDevice).sort((a, b) => a.hostname.localeCompare(b.hostname));
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort2);
      controller.signal.removeEventListener("abort", onAbort);
      controller.abort();
    }
  }
};

// node_modules/@esp-vision/device-core/src/device_python.js
function checkAbort(signal) {
  if (signal !== void 0 && signal !== null && !(signal instanceof AbortSignal)) {
    throw new TypeError("signal must be an AbortSignal");
  }
  if (signal?.aborted) {
    throw signal.reason instanceof Error ? signal.reason : Object.assign(new Error("Operation aborted"), { name: "AbortError" });
  }
}
function snapshotRequest(request, fields2, label = "operation") {
  if (!request || typeof request !== "object" || Array.isArray(request) || ![Object.prototype, null].includes(Object.getPrototypeOf(request))) {
    throw new TypeError(`Expected a ${label} request object`);
  }
  for (const key of Reflect.ownKeys(request)) {
    if (!fields2.includes(key)) throw new TypeError(`Unknown ${label} parameter: ${String(key)}`);
  }
  const snapshot = { ...request };
  checkAbort(snapshot.signal);
  return snapshot;
}
function validateDevicePath(path, { root = false } = {}) {
  if (typeof path !== "string" || !path.startsWith("/") || !root && path === "/" || new TextEncoder().encode(path).length > 123 || /[\x00-\x1f\x7f\\"]/.test(path) || path.includes("..") || path.includes("//") || path.length > 1 && path.endsWith("/")) {
    throw Object.assign(new TypeError("Expected an absolute device path within the firmware path limit"), { code: "INVALID_PATH" });
  }
  return path;
}
function deviceBusy() {
  return Object.assign(new Error("Device Python interpreter is busy"), { code: "DEVICE_BUSY" });
}
async function withDeviceOperation(state, kind, operation) {
  if (state.operation || state.run) throw deviceBusy();
  const token = { kind, interactive: false };
  state.operation = token;
  try {
    return await operation(token);
  } finally {
    if (state.operation === token) state.operation = null;
  }
}
function validateRequest(request) {
  if (!request || typeof request !== "object" || Array.isArray(request)) throw new TypeError("Expected a Python execution request");
  const source = Object.hasOwn(request, "source");
  const path = Object.hasOwn(request, "path");
  if (source === path) throw new TypeError("Specify exactly one of source or path");
  if (source && typeof request.source !== "string") throw new TypeError("Python source must be a string");
  if (path) validateDevicePath(request.path);
  const completion = request.completion ?? "wait";
  if (!["wait", "start"].includes(completion)) throw new TypeError("Python completion must be wait or start");
  if (request.timeout !== void 0 && request.timeout !== null && (!Number.isFinite(request.timeout) || request.timeout <= 0)) throw new RangeError("Python timeout must be positive or null");
  if (request.maxOutputChars !== void 0 && (!Number.isSafeInteger(request.maxOutputChars) || request.maxOutputChars < 0)) throw new RangeError("maxOutputChars must be a nonnegative integer");
  if (completion === "start" && request.timeout !== void 0) throw new TypeError("timeout only applies to completion wait");
  return { source, completion };
}
function createPythonApi({ session, state = {} }) {
  let sequence = 0;
  const normalize = (result, path, limit) => {
    const output = (typeof result === "string" ? result : result?.output ?? "").replace(/\r/g, "");
    return {
      ok: result?.ok ?? true,
      path,
      output: limit === void 0 ? output : output.slice(0, limit),
      outputTruncated: Boolean(result?.outputTruncated || limit !== void 0 && output.length > limit)
    };
  };
  return Object.freeze({
    async input(data) {
      if (typeof data !== "string" && !(data instanceof Uint8Array)) throw new TypeError("Python input must be a string or Uint8Array");
      if (data instanceof Uint8Array) data = new Uint8Array(data);
      if (state.operation?.interactive) return session.repl.writeStdin(data);
      return withDeviceOperation(state, "python.input", () => session.repl.writeStdin(data));
    },
    async execute(request) {
      request = snapshotRequest(request, ["source", "path", "completion", "timeout", "signal", "maxOutputChars"], "Python execution");
      const { source, completion } = validateRequest(request);
      const { signal = null, timeout = null, maxOutputChars } = request;
      checkAbort(signal);
      if (state.operation || state.run || session.runCapture || session.runStarting) throw deviceBusy();
      const token = { kind: "python.execute", interactive: false };
      state.operation = token;
      const temporary = source && completion === "start";
      const path = source ? temporary ? `/.__evcore_${Date.now().toString(36)}_${++sequence}.py` : null : request.path;
      const run = { path, completion, status: "starting" };
      state.run = run;
      let released = false;
      const release = async (failed = false) => {
        if (released) return;
        released = true;
        try {
          if (temporary && session.state === "ready") {
            if (failed && session.stopForRepl) {
              const ready = await session.stopForRepl({ timeout: 3e3 });
              if (!ready) throw Object.assign(new Error("Cannot clean up Python source until REPL is ready"), { code: "REPL_UNAVAILABLE" });
            }
            await session.repl.removeFile(path);
          }
        } finally {
          if (state.operation === token) state.operation = null;
          if (state.run === run) state.run = null;
        }
      };
      try {
        if (completion === "wait") {
          run.status = "running";
          const result = source ? await session.executePython(request.source, { timeout, signal }) : await session.runScript(path, void 0, { timeout, signal, maxOutputChars, inlineCompletion: true });
          await release();
          return normalize(result, path, maxOutputChars);
        }
        const started = await session.startScript(path, source ? request.source : void 0, { signal, maxOutputChars, inlineCompletion: true });
        run.status = "running";
        token.interactive = true;
        const done = started.done.then((result) => normalize(result, path, maxOutputChars)).then(async (result) => {
          await release();
          return result;
        }, async (error2) => {
          try {
            await release(true);
          } catch (_cleanupError) {
          }
          throw error2;
        });
        done.catch(() => {
        });
        return { ok: true, path, done };
      } catch (error2) {
        try {
          await release(true);
        } catch (_cleanupError) {
        }
        throw error2;
      }
    }
  });
}

// node_modules/@esp-vision/device-core/src/device_files.js
function requestObject(request) {
  if (!request || typeof request !== "object" || Array.isArray(request)) throw new TypeError("Expected a file operation request");
  return request;
}
function createFilesApi({ session, state = {} }) {
  const operate = (kind, request, fn) => {
    requestObject(request);
    checkAbort(request.signal);
    validateDevicePath(request.path, { root: kind === "list" });
    return withDeviceOperation(state, `files.${kind}`, async () => {
      if (session.runCapture || session.runStarting) throw Object.assign(new Error("Device Python interpreter is busy"), { code: "DEVICE_BUSY" });
      return fn();
    });
  };
  return Object.freeze({
    async list(request = {}) {
      request = snapshotRequest(request, ["path", "recursive", "signal"], "files.list");
      const options2 = { path: "/", recursive: false, ...request };
      if (typeof options2.recursive !== "boolean") throw new TypeError("recursive must be a boolean");
      return operate("list", options2, () => session.repl.listFs(options2.path, {
        recursive: options2.recursive,
        signal: options2.signal
      }));
    },
    async read(request) {
      request = snapshotRequest(request, ["path", "encoding", "timeout", "chunkTimeout", "maxBytes", "signal"], "files.read");
      const { path, encoding = "binary", timeout = null, chunkTimeout = 3e4, maxBytes = null, signal = null } = request;
      if (!["binary", "utf-8"].includes(encoding)) throw new TypeError("File encoding must be binary or utf-8");
      if (timeout !== null && (!Number.isFinite(timeout) || timeout <= 0)) throw new RangeError("File read timeout must be positive or null");
      if (!Number.isFinite(chunkTimeout) || chunkTimeout <= 0) throw new RangeError("File read chunk timeout must be positive");
      if (maxBytes !== null && (!Number.isSafeInteger(maxBytes) || maxBytes < 0 || maxBytes > 16 * 1024 * 1024)) throw new RangeError("maxBytes must be between zero and 16 MiB");
      return operate("read", request, async () => {
        const bytes = await session.repl.readFile(path, { timeout, chunkTimeout, maxBytes, signal });
        return encoding === "binary" ? bytes : new TextDecoder().decode(bytes);
      });
    },
    async write(request) {
      request = snapshotRequest(request, ["path", "data", "overwrite", "onProgress", "signal"], "files.write");
      const { path, data, overwrite = true, onProgress = null, signal = null } = request;
      if (typeof data !== "string" && !(data instanceof Uint8Array)) throw new TypeError("File data must be a string or Uint8Array");
      if (typeof overwrite !== "boolean") throw new TypeError("overwrite must be a boolean");
      if (onProgress !== null && typeof onProgress !== "function") throw new TypeError("onProgress must be a function");
      const content = data instanceof Uint8Array ? new Uint8Array(data) : data;
      return operate("write", request, () => session.writeFile(path, content, {
        encoding: typeof data === "string" ? "utf-8" : "binary",
        mode: overwrite ? "overwrite" : "create",
        onProgress,
        signal
      }));
    },
    async remove(request) {
      request = snapshotRequest(request, ["path", "type", "signal"], "files.remove");
      const { path, type = "file", signal = null } = request;
      if (!["file", "directory"].includes(type)) throw new TypeError("Removal type must be file or directory");
      return operate("remove", request, () => type === "directory" ? session.repl.removeDir(path, { signal }) : session.repl.removeFile(path, { signal }));
    },
    async mkdir(request) {
      request = snapshotRequest(request, ["path", "recursive", "signal"], "files.mkdir");
      const { path, recursive = false, signal = null } = request;
      if (typeof recursive !== "boolean") throw new TypeError("recursive must be a boolean");
      return operate("mkdir", request, async () => {
        const directories = recursive ? path.split("/").filter(Boolean).map((_part, index, parts) => "/" + parts.slice(0, index + 1).join("/")) : [path];
        for (const directory of directories) {
          checkAbort(signal);
          const exists = recursive ? `
 if r==17:
  try:r=0 if os.stat(p)[0]&16384 else 20
  except OSError as e:r=e.args[0]` : "";
          const assignment = `p=${JSON.stringify(directory)}`;
          const body = `r=0
try:os.mkdir(p)
except OSError as e:
 r=e.args[0]${exists}
print('__EVMK__',r)`;
          let command = `import os
${assignment}
${body}`;
          if (evReplExecInputBytes(command) > (session.repl.inputMaxBytes ?? 511)) {
            await session.repl.execPy(assignment, { signal });
            checkAbort(signal);
            command = `import os
${body}`;
          }
          const response = await session.repl.execPy(command, { signal });
          const match = /(?:^|\n)__EVMK__\s+(\d+)\s*$/.exec(response.trim());
          if (!match) throw Object.assign(new Error("Incomplete directory creation response"), { code: "DEVICE_DIRECTORY_WRITE_INCOMPLETE" });
          const errno = Number(match[1]);
          if (errno) throw Object.assign(new Error(`Cannot create directory ${directory}: OSError ${errno}`), { code: "FILESYSTEM_ERROR", errno });
        }
        return { ok: true };
      });
    }
  });
}

// node_modules/@esp-vision/device-core/src/device_operations.js
function failure(code, message) {
  return Object.assign(new Error(message), { code });
}
function record(value, keys, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new TypeError(`${label} must be an object`);
  for (const key of Object.keys(value)) if (!keys.includes(key)) throw new TypeError(`Unknown ${label} field: ${key}`);
}
function options(value, fallback) {
  const { timeout = fallback, signal } = value;
  if (!Number.isFinite(timeout) || timeout <= 0) throw new RangeError("timeout must be positive");
  if (signal !== void 0 && (!signal || typeof signal.addEventListener !== "function" || typeof signal.aborted !== "boolean")) throw new TypeError("signal must be an AbortSignal");
  aborted(signal);
  return { timeout, signal };
}
function aborted(signal) {
  if (!signal?.aborted) return;
  if (signal.reason instanceof Error) throw signal.reason;
  throw Object.assign(new Error("Device operation cancelled"), { name: "AbortError" });
}
function pause(ms, signal) {
  return new Promise((resolve2, reject) => {
    const cleanup = () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", cancel);
    };
    const cancel = () => {
      cleanup();
      try {
        aborted(signal);
      } catch (error2) {
        reject(error2);
      }
    };
    const timer = setTimeout(() => {
      cleanup();
      resolve2();
    }, ms);
    signal?.addEventListener("abort", cancel, { once: true });
    if (signal?.aborted) cancel();
  });
}
function supported(session, feature) {
  if (!session.hasFeature(feature)) throw failure("UNSUPPORTED_OPERATION", `Firmware does not support ${feature}`);
}
function createDeviceOperations({ session, state = {} }) {
  const api = {
    async inspect(request = {}) {
      record(request, ["fields", "timeout", "signal"], "inspect");
      const opts = options(request, 5e3);
      const fields2 = request.fields ?? ["identity", "capabilities", "runtime"];
      if (!Array.isArray(fields2) || !fields2.length || fields2.some((field) => !["identity", "capabilities", "runtime", "network", "storage"].includes(field))) throw new TypeError("fields must name identity, capabilities, runtime, network or storage");
      const result = {};
      for (const field of new Set(fields2)) {
        aborted(opts.signal);
        if (field === "identity") result.identity = session.identity ? structuredClone(session.identity) : null;
        if (field === "capabilities") result.capabilities = structuredClone(session.capabilities);
        if (field === "runtime") result.runtime = {
          ...structuredClone(session.snapshot()),
          vmReady: session.vmReady,
          vmEpoch: session.vmEpoch,
          run: state.run ? { path: state.run.path ?? null, completion: state.run.completion, status: state.run.status } : null
        };
        if (field === "network") {
          supported(session, "network.background");
          result.network = await session.networkStatus(opts);
        }
        if (field === "storage") {
          supported(session, "storage.writer.lease");
          result.storage = {};
          for (const volume of ["flash", "sd"]) result.storage[volume] = await session.rpc("device.control", { action: "storage.writer.status", volume }, opts);
        }
      }
      return result;
    },
    async configure(request) {
      record(request, ["network", "timeout", "signal"], "configure");
      const opts = options(request, 45e3);
      record(request.network, ["enabled", "credentials"], "network");
      const network = { ...request.network };
      if (network.credentials && typeof network.credentials === "object") network.credentials = { ...network.credentials };
      const hasCredentials = Object.hasOwn(network, "credentials");
      const hasEnabled = Object.hasOwn(network, "enabled");
      if (!hasCredentials && !hasEnabled) throw new TypeError("network must specify enabled or credentials");
      if (hasEnabled && typeof network.enabled !== "boolean") throw new TypeError("network.enabled must be a boolean");
      if (hasCredentials && network.credentials !== null) {
        record(network.credentials, ["ssid", "password"], "credentials");
        const { ssid, password } = network.credentials;
        const encode = (value) => new TextEncoder().encode(value).length;
        if (typeof ssid !== "string" || encode(ssid) < 1 || encode(ssid) > 32 || ssid.includes("\0")) throw new TypeError("ssid must contain 1 to 32 UTF-8 bytes without NUL");
        if (typeof password !== "string" || !(password === "" || /^[\x20-\x7e]{8,63}$/.test(password) || /^[0-9a-fA-F]{64}$/.test(password))) throw new TypeError("password must be empty, 8 to 63 printable ASCII characters, or a 64-digit hexadecimal PSK");
      }
      if (hasCredentials && network.credentials === null && network.enabled === true) throw new TypeError("Cannot enable networking while clearing credentials");
      supported(session, "network.background");
      if (hasCredentials) supported(session, "network.configure");
      return withDeviceOperation(state, "configure", async () => {
        const deadline = Date.now() + opts.timeout;
        const completed = [];
        let pending = null;
        const remaining = () => {
          aborted(opts.signal);
          const timeout = deadline - Date.now();
          if (timeout <= 0) throw failure("TIMEOUT", "Network configuration deadline exceeded");
          return { timeout: Math.min(timeout, 4e3), signal: opts.signal };
        };
        const apply = async (action, invoke) => {
          const response = await invoke(remaining());
          pending = { action, operationId: response.operationId ?? null };
          if (response.accepted !== true || typeof response.operationId !== "string" || !response.operationId) throw failure("INVALID_RESPONSE", "Network change requires accepted=true and an operationId");
          if (response.operationId) {
            while (true) {
              const status = await session.networkStatus(remaining());
              const operation = [status.operation, status.lastOperation].find((item) => item?.id === response.operationId);
              if (operation?.state === "failed") throw failure(operation.error?.code ?? "CONFIGURATION_FAILED", operation.error?.message ?? `${action} failed`);
              if (operation?.state === "succeeded") break;
              await pause(Math.min(100, remaining().timeout), opts.signal);
            }
          }
          completed.push({ ...pending });
          pending = null;
        };
        try {
          const before = await session.networkStatus(remaining());
          if (typeof before.enabled !== "boolean") throw failure("INVALID_RESPONSE", "Network status is missing enabled state");
          const desiredEnabled = network.credentials === null ? false : hasEnabled ? network.enabled : before.enabled;
          let currentEnabled = before.enabled;
          if (hasCredentials) {
            if (network.credentials === null) {
              await apply("network.forget", (rpcOpts) => session.forgetNetwork(rpcOpts));
              currentEnabled = false;
            } else {
              await apply("network.configure", (rpcOpts) => session.configureNetwork(network.credentials, rpcOpts));
              currentEnabled = true;
            }
          }
          if (currentEnabled !== desiredEnabled) await apply("network.enable", (rpcOpts) => session.setNetworkEnabled(desiredEnabled, rpcOpts));
          return { ok: true, completed, network: await session.networkStatus(remaining()) };
        } catch (error2) {
          error2.completed = completed;
          if (pending) error2.pending = pending;
          throw error2;
        }
      });
    },
    async control(request) {
      record(request, ["action", "mode", "timeout", "signal"], "control");
      const opts = options(request, 15e3);
      if (!["stop", "reset", "bootloader"].includes(request.action)) throw new TypeError("action must be stop, reset or bootloader");
      if (request.action === "reset" && !["soft", "hard"].includes(request.mode)) throw new TypeError("reset requires mode soft or hard");
      if (request.action !== "reset" && Object.hasOwn(request, "mode")) throw new TypeError("mode is only valid for reset");
      if (state.operation && state.operation.kind !== "python.execute") throw failure("DEVICE_BUSY", "Another device operation is active");
      const invoke = async () => {
        if (request.action === "stop") {
          if (session.hasFeature("device.control")) return session.rpc("device.control", { action: "stop" }, opts);
          await session.writeFrame("repl.signal", "signal", null, new Uint8Array([3]), opts);
          return { ok: true };
        }
        return session.control(request.action === "reset" ? `${request.mode}-reset` : "bootloader", opts);
      };
      if (state.operation?.kind === "python.execute") return invoke();
      return withDeviceOperation(state, "control", invoke);
    },
    async capture(request) {
      record(request, ["source", "format", "quality", "timeout", "signal"], "capture");
      const opts = options(request, 15e3);
      if (!["camera", "screen"].includes(request.source)) throw new TypeError("source must be camera or screen");
      if (request.format !== void 0 && request.format !== "jpeg") throw new TypeError("Only jpeg capture is supported");
      if (request.quality !== void 0 && (!Number.isInteger(request.quality) || request.quality < 1 || request.quality > 100)) throw new RangeError("quality must be an integer from 1 to 100");
      const method = request.source === "camera" ? "debug.capture_frame" : "debug.capture_screen";
      supported(session, method);
      return withDeviceOperation(state, "capture", () => session.captureImage(method, request.quality === void 0 ? {} : { quality: request.quality }, opts));
    }
  };
  return Object.freeze(api);
}

// node_modules/@esp-vision/device-core/src/firmware_flash.js
async function firmwareSha256(bytes) {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}
function firmwareMode(mode = "update") {
  if (!["update", "install"].includes(mode)) throw new TypeError("Firmware mode must be update or install");
  return mode;
}
async function validateFirmwareImage(image, bytes, { mode = "update" } = {}) {
  firmwareMode(mode);
  if (image.evMuxVersion !== 4) throw new Error("Only approved EV-MUX v4 firmware can be installed");
  if (!(bytes instanceof Uint8Array) || bytes.byteLength !== image.bytes) throw new Error("Firmware image size does not match the approved build");
  const limit = mode === "install" ? image.flashSize : image.partitionSize;
  if (!Number.isSafeInteger(image.offset) || !Number.isSafeInteger(limit) || image.offset < 0 || image.bytes <= 0 || image.bytes > limit || mode === "install" && image.offset !== 0) throw new Error("Invalid firmware image bounds");
  if (await firmwareSha256(bytes) !== image.sha256) throw new Error("Firmware SHA-256 does not match the approved build");
  if (mode === "install") {
    const segments = [image.bootloader, image.partitionTable, image.application];
    let end = 0;
    for (const segment of segments) {
      if (!segment || !Number.isSafeInteger(segment.offset) || !Number.isSafeInteger(segment.bytes) || segment.offset < end || segment.bytes <= 0 || segment.offset + segment.bytes > bytes.byteLength || !/^[a-f0-9]{64}$/.test(segment.sha256 ?? "")) throw new Error("Complete image requires ordered, non-overlapping bootloader, partition table and application metadata");
      if (await firmwareSha256(bytes.subarray(segment.offset, segment.offset + segment.bytes)) !== segment.sha256) throw new Error("Complete image does not contain the approved bootloader, partition table and application");
      end = segment.offset + segment.bytes;
    }
  }
  return bytes;
}
var FirmwareFlashSession = class {
  constructor(loader, image, { reset = () => loader.hardReset(), mode = "update" } = {}) {
    this.mode = firmwareMode(mode);
    this.loader = loader;
    this.reset = reset;
    this.image = image;
    this.state = "idle";
    this.stub = null;
  }
  async connect(bytes) {
    if (this.state !== "idle") throw new Error("Firmware loader is already in use");
    this.state = "connecting";
    try {
      await validateFirmwareImage(this.image, bytes, { mode: this.mode });
      await this.loader.initialize();
      const revisionMatches = this.image.chipRevision !== void 0 ? this.loader.chipRevision === this.image.chipRevision : Number.isInteger(this.image.chipRevisionMin) && Number.isInteger(this.image.chipRevisionMax) && this.loader.chipRevision >= this.image.chipRevisionMin && this.loader.chipRevision <= this.image.chipRevisionMax;
      if (this.loader.chipFamily !== this.image.chipFamily || !revisionMatches) {
        throw new Error("Chip or silicon revision does not match the approved board firmware");
      }
      const security = await this.loader.getSecurityInfo();
      if (!Number.isSafeInteger(security.flags) || !Number.isSafeInteger(security.flashCryptCnt)) {
        throw new Error("Cannot qualify the device ROM security mode");
      }
      const encrypted = security.flashCryptCnt.toString(2).replace(/0/g, "").length % 2 === 1;
      if ((security.flags & 1) !== 0 || encrypted) throw new Error("Secure boot or encrypted devices require their signed flashing workflow");
      this.stub = await this.loader.runStub(true);
      if (this.mode === "install") {
        if (typeof this.stub.flashId !== "function") throw new Error("Installation requires ROM flash capacity detection (flashId)");
        const id = await this.stub.flashId();
        const capacity = id >>> 16 & 255;
        if (!Number.isSafeInteger(id) || id <= 0 || id > 16777215 || capacity < 18 || capacity > 30 || 2 ** capacity < this.image.flashSize) throw new Error("Detected flash is unknown or smaller than the approved complete image layout");
      } else {
        const table = this.image.partitionTable;
        const existing = await this.stub.readFlash(table.offset, table.bytes);
        if (await firmwareSha256(existing) !== table.sha256) throw new Error("Partition layout differs; select explicit install mode to replace the layout");
      }
      this.state = "connected";
    } catch (error2) {
      await this.disconnect();
      throw error2;
    }
  }
  async flash(bytes, { onProgress = () => {
  }, onPhase = () => {
  } } = {}) {
    if (this.state !== "connected") throw new Error("Connect and validate the device before flashing");
    this.state = "flashing";
    try {
      await validateFirmwareImage(this.image, bytes, { mode: this.mode });
      onPhase(this.mode === "install" ? "Installing complete firmware; existing data in the written range will be replaced" : "Writing application; bootloader, partition table, NVS and user files are preserved");
      await this.stub.flashData(
        bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
        (written, total) => onProgress(total ? Math.min(80, Math.round(written / total * 80)) : 0),
        this.image.offset,
        false
      );
      onPhase(this.mode === "install" ? "Verifying the complete installation image" : "Verifying the complete application image");
      const readback = new Uint8Array(bytes.byteLength);
      for (let offset = 0; offset < bytes.byteLength; offset += 65536) {
        const count = Math.min(65536, bytes.byteLength - offset);
        const chunk = await this.stub.readFlash(
          this.image.offset + offset,
          count,
          void 0,
          { chunkSize: 65536, blockSize: 1024, maxInFlight: 1 }
        );
        if (chunk.byteLength !== count) throw new Error("Written firmware readback is incomplete");
        readback.set(chunk, offset);
        onProgress(80 + Math.floor(20 * (offset + count) / bytes.byteLength));
      }
      if (readback.byteLength !== bytes.byteLength || await firmwareSha256(readback) !== this.image.sha256) throw new Error("Written firmware verification failed; keep the device in download mode for recovery");
      this.state = "verified";
      try {
        if (this.loader.chipFamily === 12928) {
          const address = 1343291400, mask = 4;
          const before = await this.stub.readRegister(address);
          if (!Number.isInteger(before) || before < 0 || before > 4294967295) throw new Error("Invalid P4 system control register");
          if (before & mask) await this.stub.writeRegister(address, 0, mask);
          const after = await this.stub.readRegister(address);
          if (after !== (before & ~mask) >>> 0) throw new Error("P4 normal boot latch verification failed");
        }
        await this.reset();
      } catch (error2) {
        onPhase("Firmware verified. Automatic reset did not complete; wait for runtime reconnection or press RESET.");
        return { verified: true, needsReset: true, resetError: { code: error2?.code ?? "RESET_FAILED", message: error2?.message ?? String(error2) } };
      }
      onPhase("Firmware verified and reset. Reconnect in the IDE to verify EV-MUX v4.");
      return { verified: true, needsReset: false };
    } catch (error2) {
      this.state = "error";
      throw error2;
    } finally {
      await this.disconnect();
    }
  }
  async disconnect() {
    if (this.state === "closed") return;
    this.state = "closed";
    await this.loader.disconnect();
  }
};

// node_modules/@esp-vision/device-core/src/firmware_io.js
var MAX_FIRMWARE_BYTES = 256 * 1024 * 1024;
var MAX_MANIFEST_BYTES = 4 * 1024 * 1024;
var OFFICIAL_ROOT = "https://dl.espressif.com/AE/esp-vision/";
var SHA256 = /^[a-f0-9]{64}$/;
var SOURCE_COMMIT = /^[a-f0-9]{40}$/;
function firmwareUrl(value, { official = false } = {}) {
  if (typeof value !== "string") throw new TypeError("Firmware URLs must use HTTPS");
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new TypeError("Firmware URLs must use HTTPS");
  }
  if (url.protocol !== "https:" || url.username || url.password || url.hash || official && (!url.href.startsWith(OFFICIAL_ROOT) || url.search || /%2f|%5c|%2e/i.test(url.pathname))) throw new TypeError("Invalid firmware HTTPS URL or official source");
  return url;
}
async function responseBytes(response, { maxBytes, expectedBytes, signal } = {}) {
  const limit = Math.min(maxBytes, expectedBytes ?? maxBytes);
  const advertised = response.headers?.get?.("content-length");
  if (advertised !== null && advertised !== void 0 && (!/^\d+$/.test(advertised) || Number(advertised) > limit)) throw new RangeError("Firmware response exceeds approved byte limit");
  let bytes;
  if (response.body?.getReader) {
    const reader = response.body.getReader(), chunks = [];
    let length = 0;
    const abort2 = () => {
      void reader.cancel().catch(() => {
      });
    };
    signal?.addEventListener("abort", abort2, { once: true });
    try {
      for (; ; ) {
        signal?.throwIfAborted();
        const { done, value } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > limit) throw new RangeError("Firmware response exceeds approved byte limit");
        chunks.push(value);
      }
      bytes = new Uint8Array(length);
      let offset = 0;
      for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.byteLength;
      }
    } catch (error2) {
      await reader.cancel().catch(() => {
      });
      throw error2;
    } finally {
      signal?.removeEventListener("abort", abort2);
      reader.releaseLock();
    }
  } else if (response.arrayBuffer) bytes = new Uint8Array(await response.arrayBuffer());
  else if (response.text) bytes = new TextEncoder().encode(await response.text());
  else throw new TypeError("Firmware response must expose bytes");
  signal?.throwIfAborted();
  if (bytes.byteLength > limit) throw new RangeError("Firmware response exceeds approved byte limit");
  if (expectedBytes !== void 0 && bytes.byteLength !== expectedBytes) throw new Error("Firmware response size does not match the approved build");
  return bytes;
}
async function downloadBytes(url, { fetch: fetcher = globalThis.fetch, signal, maxBytes, expectedBytes, official = false, immutable = false } = {}) {
  firmwareUrl(url, { official });
  if (typeof fetcher !== "function") throw new TypeError("Provide fetch or in-memory firmware bytes");
  signal?.throwIfAborted();
  const request = (cache) => fetcher(url, { signal, cache, redirect: "error" });
  let response;
  try {
    response = await request(immutable ? "default" : "no-store");
  } catch (error2) {
    if (!immutable || signal?.aborted || error2?.name !== "TypeError") throw error2;
    response = await request("no-store");
  }
  if (!response.ok) throw Object.assign(new Error(`Firmware download failed: HTTP ${response.status}`), { code: "FIRMWARE_DOWNLOAD_FAILED" });
  if (response.url) firmwareUrl(response.url, { official });
  return responseBytes(response, { maxBytes, expectedBytes, signal });
}

// node_modules/@esp-vision/device-core/src/firmware_release.js
function validateFirmwareRelease(value, mode = "update") {
  if (!value || typeof value.board !== "string" || !value.board || typeof value.version !== "string" || !value.version) throw new TypeError("Release requires board and version");
  const image = value.image;
  const revisionValid = image?.chipRevision !== void 0 ? Number.isSafeInteger(image.chipRevision) && image.chipRevision >= 0 : Number.isSafeInteger(image?.chipRevisionMin) && image.chipRevisionMin >= 0 && Number.isSafeInteger(image?.chipRevisionMax) && image.chipRevisionMax >= image.chipRevisionMin;
  if (!image || image.evMuxVersion !== 4 || !Number.isSafeInteger(image.chipFamily) || image.chipFamily < 0 || !revisionValid || !Number.isSafeInteger(image.offset) || image.offset < 0 || !Number.isSafeInteger(image.bytes) || image.bytes <= 0 || !Number.isSafeInteger(image.partitionSize) || image.bytes > image.partitionSize || !/^[a-f0-9]{64}$/.test(image.sha256 ?? "") || !Number.isSafeInteger(image.partitionTable?.offset) || image.partitionTable.offset < 0 || !Number.isSafeInteger(image.partitionTable?.bytes) || image.partitionTable.bytes <= 0 || !/^[a-f0-9]{64}$/.test(image.partitionTable?.sha256 ?? "")) throw new TypeError("Release requires complete EV-MUX v4 application/chip/partition/SHA-256 metadata");
  if (mode === "install") {
    const install = value.install;
    if (!install || install.offset !== 0 || !Number.isSafeInteger(install.bytes) || install.bytes <= 0 || !Number.isSafeInteger(install.flashSize) || install.flashSize < install.bytes || install.flashSize > 2 ** 30 || !Number.isInteger(Math.log2(install.flashSize)) || install.flashSize < 2 ** 18 || !/^[a-f0-9]{64}$/.test(install.sha256 ?? "") || !install.bootloader || !Number.isSafeInteger(install.chipRevisionMin) || !Number.isSafeInteger(install.chipRevisionMax) || install.chipRevisionMin < (image.chipRevision ?? image.chipRevisionMin) || install.chipRevisionMax > (image.chipRevision ?? image.chipRevisionMax) || install.chipRevisionMin < 0 || install.chipRevisionMax < install.chipRevisionMin) throw Object.assign(new TypeError("Release lacks qualified complete-install metadata"), { code: "FIRMWARE_INSTALL_UNAVAILABLE" });
    let end = 0;
    for (const part of [install.bootloader, image.partitionTable, image]) {
      if (!Number.isSafeInteger(part.offset) || !Number.isSafeInteger(part.bytes) || part.bytes <= 0 || part.offset < end || part.offset + part.bytes > install.bytes || !/^[a-f0-9]{64}$/.test(part.sha256 ?? "")) throw new TypeError("Invalid complete-install segment bounds or hashes");
      end = part.offset + part.bytes;
    }
  }
  if (image.source !== void 0) {
    const source = image.source, install = value.install;
    if (!source || typeof source !== "object" || Array.isArray(source) || !Number.isSafeInteger(source.bytes) || source.bytes <= 0 || source.bytes > MAX_FIRMWARE_BYTES || !Number.isSafeInteger(source.offset) || source.offset < 0 || source.offset !== image.offset || !Number.isSafeInteger(source.offset + image.bytes) || source.offset + image.bytes > source.bytes || !/^[a-f0-9]{64}$/.test(source.sha256 ?? "") || source.url !== image.url || !install || source.url !== install.url || source.bytes !== install.bytes || source.sha256 !== install.sha256) throw new TypeError("Invalid complete BIN source bounds or install consistency");
    firmwareUrl(source.url);
    if (mode !== "install") validateFirmwareRelease(value, "install");
  }
  return structuredClone(value);
}

// node_modules/@esp-vision/device-core/src/firmware_feed.js
async function loadOfficialFirmware({ board, version, fetch: fetcher = globalThis.fetch, signal } = {}) {
  if (board !== void 0 && !validName(board, 96)) throw new TypeError("board must be a non-empty board string");
  if (version !== void 0 && !validName(version)) throw new TypeError("version must be a non-empty firmware version string");
  const { parse: parse2 } = await Promise.resolve().then(() => (init_dist(), dist_exports));
  const get = async (url, optional = false) => {
    signal?.throwIfAborted();
    const response = await fetcher(url, { signal, cache: "no-store" });
    if (optional && response.status === 404) return null;
    if (!response.ok) throw Object.assign(new Error(`Official firmware request failed: HTTP ${response.status}`), { code: "FIRMWARE_DOWNLOAD_FAILED" });
    return response;
  };
  const config = parse2(await (await get(OFFICIAL_ROOT + "config.toml")).text());
  if (Object.hasOwn(config, "publication")) {
    const publication = validatePublication(config.publication);
    const selected = publication.releases.find((entry) => entry.version === (version ?? publication.version));
    if (!selected || board && !selected.boards.includes(board)) throw unavailable();
    const manifest = await loadReleaseManifest({
      url: selected.manifestUrl,
      sha256: selected.manifestSha256,
      version: selected.version,
      boards: selected.boards,
      sourceCommit: selected.version === publication.version ? publication.sourceCommit : void 0,
      fetch: fetcher,
      signal
    });
    return { ...manifest, releases: manifest.releases.filter((entry) => !board || entry.board === board), publication };
  }
  const app = config["esp-vision"], web = config.website;
  if (!app?.image || !Array.isArray(web?.releases) || typeof web.binaryNameTemplate !== "string") throw new TypeError("Invalid official firmware index");
  const boards = Object.keys(app.image).filter((name) => !board || name === board);
  const knownVersions = [...new Set([web.release, ...web.releases].filter((value) => typeof value === "string" && value))];
  if (version !== void 0 && !knownVersions.includes(version)) throw unavailable();
  const versions = version === void 0 ? knownVersions : [version];
  if (versions.length > 256 || boards.length > 64) throw new RangeError("Official firmware index exceeds limits");
  const releases = [];
  for (const version2 of versions) for (const name of boards) {
    const metadata = await get(`${OFFICIAL_ROOT}firmware/${encodeURIComponent(name)}/${encodeURIComponent(version2)}.json`, true);
    if (metadata) {
      const entry = await metadata.json();
      if (entry.board !== name || entry.version !== version2 || new URL(entry.image?.url).origin !== "https://dl.espressif.com") throw new TypeError("Official firmware metadata identity/URL mismatch");
      if (entry.install && new URL(entry.install.url).origin !== "https://dl.espressif.com") throw new TypeError("Official install URL mismatch");
      releases.push(entry);
    } else {
      const file = web.binaryNameTemplate.replace("{board}", name).replace("{tag}", version2);
      const url = new URL(file, config.firmware_images_url);
      if (url.origin !== "https://dl.espressif.com") throw new TypeError("Invalid official image URL");
      releases.push({ board: name, version: version2, compatible: false, reason: "UPDATE_METADATA_UNAVAILABLE", downloadUrl: url.href });
    }
  }
  return { schemaVersion: 1, releases };
}
function validName(value, max = 255) {
  return typeof value === "string" && value.length > 0 && value.length <= max && value.trim() === value;
}
function unavailable() {
  return Object.assign(new Error("Requested firmware version is unavailable"), { code: "FIRMWARE_VERSION_UNAVAILABLE" });
}
function descriptor(value) {
  if (!value || typeof value !== "object" || Array.isArray(value) || !validName(value.version) || !SHA256.test(value.manifestSha256 ?? "") || !Array.isArray(value.boards) || !value.boards.length || value.boards.length > 64 || value.boards.some((board) => !validName(board, 96)) || new Set(value.boards).size !== value.boards.length) throw new TypeError("Invalid publication manifest reference");
  firmwareUrl(value.manifestUrl, { official: true });
}
function validatePublication(value) {
  if (!value || value.schemaVersion !== 1 || !SOURCE_COMMIT.test(value.sourceCommit ?? "") || !Array.isArray(value.releases) || !value.releases.length || value.releases.length > 256) throw new TypeError("Invalid official publication index");
  if (!validName(value.version) || !SHA256.test(value.manifestSha256 ?? "")) throw new TypeError("Invalid publication current manifest reference");
  firmwareUrl(value.manifestUrl, { official: true });
  const seen = /* @__PURE__ */ new Set();
  for (const item of value.releases) {
    descriptor(item);
    if (seen.has(item.version)) throw new TypeError("Duplicate publication version");
    seen.add(item.version);
  }
  const current = value.releases.find((item) => item.version === value.version);
  if (!current || current.manifestUrl !== value.manifestUrl || current.manifestSha256 !== value.manifestSha256) throw new TypeError("Publication current manifest reference differs from its history");
  return structuredClone(value);
}
function validateWebsite(website, version, sourceCommit) {
  if (!website || typeof website !== "object" || Array.isArray(website) || typeof website.schemaVersion !== "string" || !/^\d+\.\d+\.\d+$/.test(website.schemaVersion) || website.release !== version || !Array.isArray(website.releases) || website.releases.length > 256 || !website.releases.includes(version) || website.releases.some((item) => !validName(item)) || typeof website.binaryNameTemplate !== "string" || website.binaryNameTemplate.length > 255 || !website.binaryNameTemplate.includes("{board}") || !website.binaryNameTemplate.includes("{tag}") || !Array.isArray(website.boards) || website.boards.length > 64 || !Array.isArray(website.models) || website.models.length > 256) throw new TypeError("Invalid release manifest website snapshot");
  const boards = /* @__PURE__ */ new Set(), models = /* @__PURE__ */ new Set();
  for (const board of website.boards) {
    if (!board || !validName(board.board, 96) || !validName(board.slug, 96) || !validName(board.name) || typeof board.flashable !== "boolean" || boards.has(board.board)) throw new TypeError("Invalid or duplicate manifest website board");
    if (board.docsUrl !== void 0) firmwareUrl(board.docsUrl);
    boards.add(board.board);
  }
  for (const model of website.models) {
    if (!model || !validName(model.slug, 96) || models.has(model.path) || !Number.isSafeInteger(model.sizeBytes) || model.sizeBytes <= 0 || model.sizeBytes > MAX_FIRMWARE_BYTES || typeof model.path !== "string" || !model.path.startsWith("models/") || model.path.length > 512 || model.path.split("/").some((part) => !part || part === "." || part === "..") || model.downloadUrl !== `https://raw.githubusercontent.com/espressif/esp-vision/${sourceCommit}/${model.path}`) throw new TypeError("Invalid manifest model or unpinned model URL");
    const modelUrl = firmwareUrl(model.downloadUrl);
    if (modelUrl.search || !modelUrl.pathname.startsWith(`/espressif/esp-vision/${sourceCommit}/models/`) || /%2f|%5c|%2e/i.test(modelUrl.pathname)) throw new TypeError("Invalid manifest model path or source commit boundary");
    models.add(model.path);
  }
}
function validateManifest(value, { version, sourceCommit, boards } = {}) {
  if (!value || value.schemaVersion !== 1 || !validName(value.version) || !["legacy", "single-bin"].includes(value.layout) || !SOURCE_COMMIT.test(value.sourceCommit ?? "") || !Number.isSafeInteger(value.pipelineId) || value.pipelineId <= 0 || version !== void 0 && value.version !== version || sourceCommit !== void 0 && value.sourceCommit !== sourceCommit || !Array.isArray(value.releases) || !value.releases.length || value.releases.length > 64) throw new TypeError("Invalid release manifest identity or bounds");
  const seen = /* @__PURE__ */ new Set();
  for (const entry of value.releases) {
    validateFirmwareRelease(entry);
    if (entry.image.bytes > MAX_FIRMWARE_BYTES || entry.install && entry.install.bytes > MAX_FIRMWARE_BYTES) throw new RangeError("Manifest firmware image exceeds byte limit");
    if (entry.version !== value.version || entry.sourceCommit !== void 0 && entry.sourceCommit !== value.sourceCommit || seen.has(entry.board)) throw new TypeError("Release manifest board/version mismatch or duplicate board");
    seen.add(entry.board);
    if (value.layout === "single-bin" !== (entry.image.source !== void 0)) throw new TypeError("Release manifest BIN layout/source mismatch");
    firmwareUrl(entry.image.url, { official: true });
    if (entry.image.source) firmwareUrl(entry.image.source.url, { official: true });
    if (entry.install) {
      validateFirmwareRelease(entry, "install");
      firmwareUrl(entry.install.url, { official: true });
    }
  }
  if (boards !== void 0 && (boards.length !== seen.size || boards.some((board) => !seen.has(board)))) throw new TypeError("Release manifest board set differs from publication reference");
  validateWebsite(value.website, value.version, value.sourceCommit);
  if (value.website.boards.some((board) => board.flashable && !seen.has(board.board))) throw new TypeError("Manifest website advertises an unqualified board");
  if (value.mcp !== void 0 && value.mcp !== null) {
    const mcp = value.mcp;
    if (!mcp || typeof mcp !== "object" || Array.isArray(mcp) || !Number.isSafeInteger(mcp.bytes) || mcp.bytes <= 0 || mcp.bytes > 16 * 1024 * 1024 || !SHA256.test(mcp.sha256 ?? "") || mcp.version !== value.version || mcp.sourceCommit !== value.sourceCommit) throw new TypeError("Invalid release manifest MCP descriptor");
    firmwareUrl(mcp.url, { official: true });
    const mcpPath = new URL(mcp.url).pathname;
    if (!mcpPath.startsWith("/AE/esp-vision/bin/mcp/") || decodeURIComponent(mcpPath.slice(mcpPath.lastIndexOf("/") + 1)) !== `mcp-pack-${value.version}.json`) throw new TypeError("Invalid release manifest MCP source");
  }
  return value;
}
async function loadReleaseManifest({ url, sha256, version, sourceCommit, boards, fetch: fetcher = globalThis.fetch, signal } = {}) {
  if (!SHA256.test(sha256 ?? "") || version !== void 0 && !validName(version) || sourceCommit !== void 0 && !SOURCE_COMMIT.test(sourceCommit) || boards !== void 0 && (!Array.isArray(boards) || !boards.length || boards.length > 64 || boards.some((board) => !validName(board, 96)) || new Set(boards).size !== boards.length)) throw new TypeError("Manifest requires a qualified SHA-256, version and source commit");
  const bytes = await downloadBytes(url, { fetch: fetcher, signal, maxBytes: MAX_MANIFEST_BYTES, official: true, immutable: true });
  if (await firmwareSha256(bytes) !== sha256) throw new Error("Release manifest SHA-256 does not match publication");
  signal?.throwIfAborted();
  const value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  return validateManifest(value, { version, sourceCommit, boards });
}

// node_modules/@esp-vision/device-core/src/firmware_updates.js
function record2(value, keys, name) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new TypeError(`${name} must be an object`);
  for (const key of Object.keys(value)) if (!keys.includes(key)) throw new TypeError(`Unknown ${name} field: ${key}`);
}
function abort(signal) {
  if (signal !== void 0 && (!signal || typeof signal.addEventListener !== "function" || typeof signal.aborted !== "boolean")) throw new TypeError("signal must be an AbortSignal");
  if (signal?.aborted) throw signal.reason instanceof Error ? signal.reason : Object.assign(new Error("Firmware operation cancelled"), { name: "AbortError" });
}
function identity(value) {
  if (!value || typeof value.board !== "string" || !value.board || typeof value.firmwareVersion !== "string" || !value.firmwareVersion) throw new TypeError("An inspected identity with board and firmwareVersion is required");
  return structuredClone(value);
}
async function download(url, fetcher, signal) {
  if (typeof url !== "string" || new URL(url).protocol !== "https:") throw new TypeError("Firmware URLs must use HTTPS");
  if (typeof fetcher !== "function") throw new TypeError("Provide fetch or an in-memory catalog/image");
  abort(signal);
  const response = await fetcher(url, { signal, cache: "no-store" });
  if (!response.ok) throw Object.assign(new Error(`Firmware download failed: HTTP ${response.status}`), { code: "FIRMWARE_DOWNLOAD_FAILED" });
  return response;
}
async function checkFirmware(request = {}, connectedIdentity) {
  record2(request, ["catalog", "identity", "version", "mode", "fetch", "signal"], "firmware.check");
  const { signal, fetch: fetcher = globalThis.fetch } = request;
  abort(signal);
  if (request.version !== void 0 && (typeof request.version !== "string" || !request.version.trim())) throw new TypeError("version must be a non-empty firmware version string");
  const mode = firmwareMode(request.mode);
  const current = identity(connectedIdentity ?? request.identity);
  const catalog = request.catalog === void 0 ? await loadOfficialFirmware({ board: current.board, version: request.version, fetch: fetcher, signal }) : typeof request.catalog === "string" ? await (await download(request.catalog, fetcher, signal)).json() : structuredClone(request.catalog);
  abort(signal);
  if (catalog?.schemaVersion !== 1 || !Array.isArray(catalog.releases)) throw new TypeError("Catalog requires schemaVersion 1 and releases ordered newest first");
  const candidates = catalog.releases.filter((item) => item?.board === current.board).map((item) => {
    if (item.compatible !== false) return validateFirmwareRelease(item);
    if (typeof item.version !== "string" || !item.version) throw new TypeError("Historical release requires a version");
    return structuredClone(item);
  });
  if (new Set(candidates.map((item) => item.version)).size !== candidates.length) throw new TypeError("Catalog must not contain duplicate versions for one board");
  const selected = request.version === void 0 ? candidates.find((item) => item.compatible !== false && (mode !== "install" || item.install)) ?? null : candidates.find((item) => item.version === request.version);
  if (request.version !== void 0 && !selected) throw Object.assign(new Error("Requested firmware version is unavailable for this board"), { code: "FIRMWARE_VERSION_UNAVAILABLE" });
  if (selected?.compatible === false) throw Object.assign(new Error("This published version lacks approved v4 update metadata"), { code: "FIRMWARE_INCOMPATIBLE" });
  if (selected) validateFirmwareRelease(selected, mode);
  return { available: selected !== null && (selected.firmwareVersion ?? selected.version) !== current.firmwareVersion, currentVersion: current.firmwareVersion, release: selected, releases: candidates };
}
async function updateFirmware(request, connectedIdentity, disconnect) {
  record2(request, ["release", "board", "mode", "data", "fetch", "openLoader", "reset", "onProgress", "onPhase", "signal"], "firmware.update");
  const { signal, fetch: fetcher = globalThis.fetch, openLoader, reset, onProgress = () => {
  }, onPhase = () => {
  } } = request;
  abort(signal);
  if (typeof openLoader !== "function" || typeof onProgress !== "function" || typeof onPhase !== "function" || reset !== void 0 && typeof reset !== "function") throw new TypeError("Firmware update requires openLoader and valid callbacks");
  const mode = firmwareMode(request.mode);
  const target = validateFirmwareRelease(request.release, mode);
  const installation = target.install ? {
    ...target.image,
    offset: target.install.offset,
    bytes: target.install.bytes,
    flashSize: target.install.flashSize,
    sha256: target.install.sha256,
    url: target.install.url,
    bootloader: target.install.bootloader,
    application: target.image,
    chipRevision: void 0,
    chipRevisionMin: target.install.chipRevisionMin,
    chipRevisionMax: target.install.chipRevisionMax
  } : null;
  const image = mode === "install" ? installation : target.image;
  const board = connectedIdentity?.board ?? request.board;
  if (!board || board !== target.board || request.board !== void 0 && request.board !== board) throw new TypeError("Firmware release does not match the connected or explicitly selected board");
  const source = mode === "update" ? image.source : void 0;
  const descriptor2 = source ?? image;
  let bytes = request.data === void 0 ? await downloadBytes(descriptor2.url, { fetch: fetcher, signal, maxBytes: MAX_FIRMWARE_BYTES, expectedBytes: descriptor2.bytes, immutable: target.image.source !== void 0 }) : request.data instanceof Uint8Array ? request.data.slice() : request.data;
  if (source) {
    if (!(bytes instanceof Uint8Array) || bytes.byteLength !== source.bytes) throw new Error("Complete BIN source size does not match the approved build");
    await validateFirmwareImage(installation, bytes, { mode: "install" });
    bytes = bytes.slice(source.offset, source.offset + image.bytes);
  }
  await validateFirmwareImage(image, bytes, { mode });
  abort(signal);
  await disconnect();
  abort(signal);
  const loader = await openLoader({ signal });
  let session;
  try {
    abort(signal);
    session = new FirmwareFlashSession(loader, image, { mode, reset: reset ? () => reset(loader) : void 0 });
    await session.connect(bytes);
    abort(signal);
    const result = await session.flash(bytes, { onProgress, onPhase });
    return { ...result, version: target.version, board: target.board, reconnected: false };
  } finally {
    if (session) await session.disconnect();
    else await loader.disconnect();
  }
}

// node_modules/@esp-vision/device-core/src/device.js
var EVENTS = /* @__PURE__ */ new Set(["python.output", "raw", "preview", "log", "state", "diagnostic", "rpc"]);
function object(value, keys, name) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new TypeError(`${name} must be an object`);
  for (const key of Object.keys(value)) if (!keys.includes(key)) throw new TypeError(`Unknown ${name} field: ${key}`);
}
function failure2(code, message) {
  return Object.assign(new Error(message), { code });
}
function cancellation(signal) {
  return signal.reason instanceof Error ? signal.reason : Object.assign(new Error("Device operation cancelled"), { name: "AbortError" });
}
function abortable(value, signal) {
  return new Promise((resolve2, reject) => {
    const abort2 = () => {
      cleanup();
      reject(cancellation(signal));
    };
    const cleanup = () => signal.removeEventListener("abort", abort2);
    signal.addEventListener("abort", abort2, { once: true });
    Promise.resolve(value).then((result) => {
      cleanup();
      resolve2(result);
    }, (error2) => {
      cleanup();
      reject(error2);
    });
    if (signal.aborted) abort2();
  });
}
var Device = class {
  #transport;
  #discovery;
  #session = null;
  #api = null;
  #state = {};
  #listeners = /* @__PURE__ */ new Map();
  #unsubscribe = null;
  #lifecycle = null;
  #connecting = false;
  #disconnecting = null;
  #generation = 0;
  #updating = false;
  constructor(options2 = {}) {
    object(options2, ["transport", "discovery"], "device options");
    this.#transport = options2.transport ?? null;
    this.#discovery = options2.discovery ? new NetworkDiscovery(options2.discovery) : null;
    this.firmware = Object.freeze({
      check: (request) => checkFirmware(request, this.#session?.identity),
      update: (request) => this.#updateFirmware(request)
    });
    this.python = Object.freeze({
      input: (data) => this.#ready().python.input(data),
      execute: (request) => this.#invoke("python", "execute", request)
    });
    this.files = Object.freeze(Object.fromEntries(["list", "read", "write", "remove", "mkdir"].map((method) => [
      method,
      (request) => this.#invoke("files", method, request)
    ])));
  }
  on(event, handler) {
    if (!EVENTS.has(event)) throw new TypeError(`Unknown device event: ${event}`);
    if (typeof handler !== "function") throw new TypeError("Event handler must be a function");
    const handlers = this.#listeners.get(event) ?? /* @__PURE__ */ new Set();
    handlers.add(handler);
    this.#listeners.set(event, handlers);
    return () => {
      handlers.delete(handler);
      if (!handlers.size) this.#listeners.delete(event);
    };
  }
  #emit(event, value) {
    for (const handler of [...this.#listeners.get(event) ?? []]) {
      try {
        handler(value);
      } catch {
        if (event !== "diagnostic") this.#emit("diagnostic", { event: "listener.error", source: event });
      }
    }
  }
  async #updateFirmware(request) {
    if (this.#updating || this.#connecting || this.#disconnecting || this.#state.operation) throw failure2("DEVICE_BUSY", "Another device operation is active");
    const identity2 = this.#session?.identity ? structuredClone(this.#session.identity) : null;
    this.#updating = true;
    try {
      return await updateFirmware(request, identity2, () => this.disconnect());
    } finally {
      this.#updating = false;
    }
  }
  #ready() {
    if (this.#updating) throw failure2("DEVICE_BUSY", "Firmware update is active");
    if (!this.#session || this.#session.state !== "ready" || !this.#api) throw failure2("DEVICE_NOT_READY", "Connect the device before invoking this operation");
    return this.#api;
  }
  async #invoke(domain, method, request = {}) {
    const api = this.#ready();
    if (!request || typeof request !== "object" || Array.isArray(request)) throw new TypeError("Device request must be an object");
    const controller = new AbortController();
    const lifecycle = this.#lifecycle.signal;
    const source = request.signal;
    if (source !== void 0 && (!source || typeof source.addEventListener !== "function" || typeof source.aborted !== "boolean")) throw new TypeError("signal must be an AbortSignal");
    const abortLifecycle = () => controller.abort(lifecycle.reason);
    const abortSource = () => controller.abort(source.reason);
    lifecycle.addEventListener("abort", abortLifecycle, { once: true });
    source?.addEventListener("abort", abortSource, { once: true });
    if (lifecycle.aborted) abortLifecycle();
    if (source?.aborted) abortSource();
    const cleanupLifecycle = () => {
      lifecycle.removeEventListener("abort", abortLifecycle);
    };
    const cleanup = () => {
      cleanupLifecycle();
      source?.removeEventListener("abort", abortSource);
    };
    try {
      const result = await api[domain][method]({ ...request, signal: controller.signal });
      if (result?.done instanceof Promise) {
        if (domain === "python" && method === "execute") cleanupLifecycle();
        result.done.then(cleanup, cleanup);
        return result;
      }
      cleanup();
      return result;
    } catch (error2) {
      cleanup();
      throw error2;
    }
  }
  discover(options2 = {}) {
    if (!this.#discovery) throw failure2("DISCOVERY_UNAVAILABLE", "Provide a discovery adapter to list LAN devices");
    return this.#discovery.list(options2);
  }
  async connect(options2 = {}) {
    object(options2, ["transport", "role", "expectedDevice", "timeout", "signal", "probeRepl"], "connect");
    const { role = "unknown", expectedDevice = null, timeout = 3e4, signal, probeRepl = true } = options2;
    if (!["unknown", "usj", "usb", "uart", "tcp"].includes(role)) throw new TypeError("role must be usj, usb, uart or tcp");
    if (!Number.isFinite(timeout) || timeout <= 0) throw new RangeError("timeout must be positive");
    if (typeof probeRepl !== "boolean") throw new TypeError("probeRepl must be a boolean");
    if (signal !== void 0 && (!signal || typeof signal.addEventListener !== "function" || typeof signal.aborted !== "boolean")) throw new TypeError("signal must be an AbortSignal");
    if (signal?.aborted) throw cancellation(signal);
    if (this.#updating || this.#connecting || this.#disconnecting || this.#session) throw failure2("DEVICE_BUSY", "Disconnect before opening another connection");
    const transport = options2.transport ?? this.#transport;
    if (typeof transport?.writeBytes !== "function" || typeof transport?.subscribe !== "function") throw new TypeError("Transport requires writeBytes(bytes) and subscribe({data,error,close})");
    this.#connecting = true;
    this.#transport = transport;
    this.#state = {};
    const generation = ++this.#generation;
    const lifecycle = this.#lifecycle = new AbortController();
    const abort2 = () => lifecycle.abort(cancellation(signal));
    signal?.addEventListener("abort", abort2, { once: true });
    const timer = setTimeout(() => lifecycle.abort(failure2("TIMEOUT", "Device connection timed out")), timeout);
    const session = this.#session = new DeviceSession({
      transport,
      EvMuxParser,
      EvRepl,
      makeEvMuxFrame,
      handlers: {
        text: (text) => this.#emit("python.output", text),
        rawText: (text) => this.#emit("raw", text),
        log: (text) => this.#emit("log", text),
        preview: (base64, metadata, bytes) => this.#emit("preview", { data: bytes.slice(), mimeType: "image/jpeg", metadata }),
        rpc: (event) => {
          this.#emit("rpc", event);
          if (event.metadata?.method === "hello" || event.metadata?.method === "network.changed") this.#emit("state", { state: session.state, reason: event.metadata.method });
        },
        rpcRequest: (event) => this.#emit("diagnostic", { event: "rpc.request", ...event }),
        rpcResponse: (event) => this.#emit("diagnostic", { event: "rpc.response", ...event }),
        rpcTimeout: (event) => this.#emit("diagnostic", { event: "rpc.timeout", ...event }),
        diagnostic: (event) => this.#emit("diagnostic", event),
        sessionLost: (event) => lost(event?.error ?? failure2("SESSION_LOST", "Device session was lost"))
      }
    });
    const lost = (error2) => {
      if (generation !== this.#generation) return;
      const reason = error2 instanceof Error ? error2 : failure2("CONNECTION_CLOSED", "Device transport closed");
      lifecycle.abort(reason);
      session.close(reason);
      if (!this.#disconnecting) {
        this.#disconnecting = this.#dispose(reason).catch(() => {
          this.#emit("diagnostic", { event: "disconnect.cleanup_failed" });
        }).finally(() => {
          this.#disconnecting = null;
        });
      }
    };
    this.#emit("state", { state: "connecting" });
    try {
      this.#unsubscribe = transport.subscribe({ data: (bytes) => {
        if (this.#session === session) session.feedBytes(bytes);
      }, error: lost, close: () => lost() });
      if (typeof this.#unsubscribe !== "function") throw new TypeError("Transport subscribe must synchronously return an unsubscribe function");
      if (transport.connect) await abortable(transport.connect({ signal: lifecycle.signal }), lifecycle.signal);
      await abortable(session.negotiate({ role, expectedDevice, probeRepl, signal: lifecycle.signal }), lifecycle.signal);
      if (lifecycle.signal.aborted || this.#session !== session) throw cancellation(lifecycle.signal);
      this.#api = {
        python: createPythonApi({ session, state: this.#state }),
        files: createFilesApi({ session, state: this.#state }),
        operations: createDeviceOperations({ session, state: this.#state })
      };
      this.#emit("state", { state: "ready", identity: structuredClone(session.identity) });
      return this.#api.operations.inspect();
    } catch (error2) {
      if (this.#disconnecting) await this.#disconnecting.catch(() => {
      });
      else if (this.#session === session) await this.#dispose(error2).catch(() => {
      });
      throw error2;
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort2);
      this.#connecting = false;
    }
  }
  async #dispose(reason = failure2("CONNECTION_CLOSED", "Device disconnected")) {
    const session = this.#session;
    const transport = this.#transport;
    ++this.#generation;
    this.#lifecycle?.abort(reason);
    let error2;
    try {
      if (session?.sessionId) await session.release();
    } catch (caught) {
      error2 = caught;
    } finally {
      session?.close(reason);
      this.#session = null;
      this.#api = null;
      try {
        this.#unsubscribe?.();
      } catch (caught) {
        error2 ??= caught;
      }
      this.#unsubscribe = null;
      try {
        await transport?.disconnect?.();
      } catch (caught) {
        error2 ??= caught;
      }
      this.#state = {};
      this.#emit("state", { state: "disconnected", reason: reason.code ?? "CONNECTION_CLOSED" });
    }
    if (error2) throw error2;
  }
  disconnect() {
    if (this.#disconnecting) return this.#disconnecting;
    if (!this.#session) return Promise.resolve();
    const done = this.#dispose();
    this.#disconnecting = done.finally(() => {
      this.#disconnecting = null;
    });
    return this.#disconnecting;
  }
  inspect(request) {
    return this.#invoke("operations", "inspect", request);
  }
  configure(request) {
    return this.#invoke("operations", "configure", request);
  }
  control(request) {
    return this.#invoke("operations", "control", request);
  }
  capture(request) {
    return this.#invoke("operations", "capture", request);
  }
};
function createDevice(options2) {
  return new Device(options2);
}

// node_modules/@esp-vision/device-core/src/node_transport.js
import { Socket } from "node:net";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
var fail = (code, message) => Object.assign(new Error(message), { code });
function subscribers() {
  let listener = null;
  return {
    subscribe(value) {
      if (listener) throw fail("TRANSPORT_BUSY", "Already subscribed");
      listener = value;
      return () => {
        listener = null;
      };
    },
    emit(event, value) {
      listener?.[event]?.(value);
    }
  };
}
function tcpTransport(options2) {
  const events = subscribers();
  let socket;
  return {
    subscribe: events.subscribe,
    connect({ signal }) {
      return new Promise((resolveConnect, reject) => {
        socket = new Socket();
        socket.setNoDelay(true);
        const abort2 = () => {
          socket.destroy();
          reject(fail("CANCELLED", "Connection cancelled"));
        };
        const cleanup = () => signal.removeEventListener("abort", abort2);
        socket.on("data", (bytes) => events.emit("data", bytes));
        socket.on("error", () => {
          const error2 = fail("TCP_ERROR", "TCP transport failed");
          cleanup();
          reject(error2);
          events.emit("error", error2);
        });
        socket.on("close", () => {
          cleanup();
          events.emit("close");
          reject(fail("TCP_CLOSED", "TCP connection closed"));
        });
        signal.addEventListener("abort", abort2, { once: true });
        if (signal.aborted) return abort2();
        socket.connect(options2.port, options2.host, () => {
          cleanup();
          resolveConnect();
        });
      });
    },
    writeBytes(bytes) {
      return new Promise((resolveWrite, reject) => socket?.writable ? socket.write(bytes, (error2) => error2 ? reject(fail("TCP_WRITE", "TCP write failed")) : resolveWrite()) : reject(fail("TCP_CLOSED", "TCP connection is closed")));
    },
    disconnect() {
      socket?.destroy();
    }
  };
}
function serialTransport(options2) {
  const events = subscribers();
  let child;
  return {
    subscribe: events.subscribe,
    connect({ signal }) {
      return new Promise((resolveConnect, reject) => {
        const adapter = fileURLToPath(new URL("./node_serial.py", import.meta.url));
        child = spawn(options2.python, ["-u", adapter, options2.serial], { stdio: ["pipe", "pipe", "pipe"] });
        let ready = false, settled = false, runtimeErrorReported = false, stderr = "";
        const abort2 = () => {
          child.kill("SIGTERM");
          if (!settled) {
            settled = true;
            reject(fail("CANCELLED", "Serial connection cancelled"));
          }
        };
        const cleanup = () => signal.removeEventListener("abort", abort2);
        const serialError = () => {
          const code = ["SERIAL_ACCESS_DENIED", "SERIAL_BUSY"].find((code2) => stderr.includes(code2)) ?? "SERIAL_ERROR";
          return fail(code, "Serial adapter failed; ensure Python, pyserial and port access are available");
        };
        const failBeforeReady = () => {
          if (settled) return;
          settled = true;
          cleanup();
          const error2 = serialError();
          reject(error2);
          events.emit("error", error2);
        };
        const reportRuntimeError = () => {
          if (runtimeErrorReported) return;
          runtimeErrorReported = true;
          events.emit("error", serialError());
        };
        child.on("error", () => {
          if (ready) reportRuntimeError();
        });
        child.stdin.on("error", () => {
          if (ready) reportRuntimeError();
        });
        child.stdout.on("data", (bytes) => events.emit("data", bytes));
        child.stderr.on("data", (bytes) => {
          if (ready) return;
          stderr = (stderr + bytes.toString()).slice(-128);
          if (stderr.split(/\r?\n/).includes("READY")) {
            ready = true;
            settled = true;
            cleanup();
            resolveConnect();
          }
        });
        child.on("close", () => {
          cleanup();
          if (!ready) failBeforeReady();
          events.emit("close");
        });
        signal.addEventListener("abort", abort2, { once: true });
        if (signal.aborted) abort2();
      });
    },
    writeBytes(bytes) {
      return new Promise((resolveWrite, reject) => child?.stdin.writable ? child.stdin.write(bytes, (error2) => error2 ? reject(fail("SERIAL_WRITE", "Serial write failed")) : resolveWrite()) : reject(fail("SERIAL_CLOSED", "Serial adapter closed")));
    },
    async disconnect() {
      if (!child?.pid || child.exitCode !== null || child.signalCode !== null) return;
      await new Promise((resolveExit) => {
        const timer = setTimeout(() => {
          child.kill("SIGKILL");
        }, 2e3);
        child.once("exit", () => {
          clearTimeout(timer);
          resolveExit();
        });
        child.stdin.end();
        child.kill("SIGTERM");
      });
    }
  };
}

// node_modules/@esp-vision/device-core/src/node_rom.js
import { spawn as spawn2 } from "node:child_process";
import { createInterface } from "node:readline";
import { fileURLToPath as fileURLToPath3 } from "node:url";

// node_modules/@esp-vision/device-core/src/node_inventory.js
import { execFile as execFile2 } from "node:child_process";
import { promisify as promisify2 } from "node:util";
import { fileURLToPath as fileURLToPath2 } from "node:url";

// node_modules/@esp-vision/device-core/src/network_discovery_node.js
var dnsName = (value) => String(value).toLowerCase().replace(/\.$/, "");
var privateAddress = (address) => /^(10\.|192\.168\.|169\.254\.)/.test(address) || /^172\.(1[6-9]|2[0-9]|3[01])\./.test(address);
function createNodeDiscovery({ createMdns, interfaceAddress } = {}) {
  return new NetworkDiscovery({ async list({ timeout, signal }) {
    signal.throwIfAborted();
    const factory = createMdns || (await Promise.resolve().then(() => __toESM(require_multicast_dns(), 1))).default;
    signal.throwIfAborted();
    const mdns = factory({ ...interfaceAddress ? { interface: interfaceAddress } : {}, bind: "0.0.0.0", reuseAddr: true });
    return new Promise((resolve2, reject) => {
      const records = /* @__PURE__ */ new Map();
      let timer, retry, receivedSequence = 0, finished = false;
      const finish = (error2) => {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        clearInterval(retry);
        signal.removeEventListener("abort", abort2);
        mdns.removeListener("response", response);
        mdns.destroy();
        if (error2) reject(error2);
        else {
          try {
            resolve2(snapshot());
          } catch (failure3) {
            reject(failure3);
          }
        }
      };
      const abort2 = () => finish(signal.reason);
      const values = (name, type) => [...records.values()].filter((r) => r.name === name && r.type === type && r.expiresAt > Date.now()).sort((a, b) => b.sequence - a.sequence);
      const snapshot = () => {
        const devices = /* @__PURE__ */ new Map();
        for (const ptr of values(ESP_VISION_DISCOVERY_SERVICE, "PTR")) {
          const instance = dnsName(ptr.data);
          const srv = values(instance, "SRV")[0], txt = values(instance, "TXT")[0];
          if (!srv || !txt) continue;
          if (!Array.isArray(txt.data) || !txt.data.every((item) => item instanceof Uint8Array)) continue;
          const metadata = /* @__PURE__ */ Object.create(null);
          let valid = true, size = 0;
          for (const item of txt.data || []) {
            const entry = new TextDecoder().decode(item);
            size += item.length + 1;
            const split = entry.indexOf("=");
            const key = entry.slice(0, split);
            if (split < 1 || key in metadata) {
              valid = false;
              break;
            }
            metadata[key] = entry.slice(split + 1);
          }
          if (!valid || size > 256 || metadata.txtvers !== "1") continue;
          if (dnsName(srv.data.target) !== dnsName(metadata.hostname + ".local")) continue;
          const addresses = values(dnsName(srv.data.target), "A").filter((r) => privateAddress(r.data));
          try {
            const candidate = normalizeDiscoveredDevice({
              deviceId: metadata.id,
              hostname: metadata.hostname,
              board: metadata.board,
              firmwareVersion: metadata.fw,
              evMuxVersion: Number(metadata.evmux),
              port: srv.data.port,
              addresses: addresses.map((r) => r.data),
              expiresAt: Math.min(ptr.expiresAt, srv.expiresAt, txt.expiresAt, ...addresses.map((r) => r.expiresAt))
            });
            const key = candidate.deviceId + ":" + candidate.port;
            const previous = devices.get(key);
            if (previous && previous.hostname === candidate.hostname) {
              previous.addresses = [.../* @__PURE__ */ new Set([...previous.addresses, ...candidate.addresses])];
              previous.expiresAt = Math.min(previous.expiresAt, candidate.expiresAt);
            } else if (!previous) devices.set(key, candidate);
          } catch {
          }
        }
        return [...devices.values()];
      };
      const query = () => {
        const questions = [{ name: ESP_VISION_DISCOVERY_SERVICE, type: "PTR" }];
        for (const ptr of values(ESP_VISION_DISCOVERY_SERVICE, "PTR")) {
          const instance = dnsName(ptr.data);
          for (const type of ["SRV", "TXT"]) if (!values(instance, type).length) questions.push({ name: instance, type });
          for (const srv of values(instance, "SRV")) if (!values(dnsName(srv.data.target), "A").length) questions.push({ name: srv.data.target, type: "A" });
        }
        try {
          mdns.query({ questions: questions.slice(0, 64) });
        } catch (error2) {
          finish(error2);
        }
      };
      const response = (packet) => {
        const now = Date.now();
        const sequence = ++receivedSequence;
        for (const [key, cached] of records) if (cached.expiresAt <= now) records.delete(key);
        for (const r of [...packet.answers || [], ...packet.additionals || []].slice(0, 256)) {
          if (!["PTR", "SRV", "TXT", "A"].includes(r.type) || !Number.isFinite(r.ttl) || r.ttl < 0) continue;
          if (r.type === "SRV" && (typeof r.data?.target !== "string" || !Number.isInteger(r.data.port) || r.data.port < 1 || r.data.port > 65535)) continue;
          if (["PTR", "A"].includes(r.type) && typeof r.data !== "string") continue;
          if (r.type === "TXT" && (!Array.isArray(r.data) || !r.data.every((item) => item instanceof Uint8Array) || r.data.reduce((size, item) => size + item.length + 1, 0) > 256)) continue;
          const name = dnsName(r.name);
          const key = name + ":" + r.type + ":" + JSON.stringify(r.data);
          if (r.ttl === 0) {
            const cached = records.get(key);
            if (cached) cached.expiresAt = Math.min(cached.expiresAt, now + 1e3);
            continue;
          }
          if (r.flush && r.type !== "PTR") {
            for (const cached of records.values()) if (cached.name === name && cached.type === r.type && cached.receivedAt < now - 1e3) cached.expiresAt = Math.min(cached.expiresAt, now + 1e3);
          }
          if (records.size < 2048 || records.has(key)) records.set(key, {
            name,
            type: r.type,
            // Detach TXT slices from the original UDP buffer; never retain whole packets.
            data: r.type === "TXT" ? r.data.map((item) => new Uint8Array(item)) : r.data,
            sequence,
            receivedAt: now,
            expiresAt: now + Math.min(r.ttl, 120) * 1e3
          });
        }
      };
      mdns.on("error", finish);
      mdns.on("response", response);
      signal.addEventListener("abort", abort2, { once: true });
      if (signal.aborted) {
        abort2();
        return;
      }
      timer = setTimeout(() => finish(), timeout);
      query();
      if (!finished) retry = setInterval(query, 500);
    });
  } });
}

// node_modules/@esp-vision/device-core/src/node_inventory.js
var defaultPython = process.platform === "win32" ? "python" : "python3";
async function listSerial({ python = defaultPython, signal, timeout = 1e4 } = {}, dependencies = {}) {
  if (!Number.isFinite(timeout) || timeout <= 0) throw new RangeError("Serial enumeration timeout must be positive");
  try {
    const run = dependencies.execFile ?? promisify2(execFile2);
    const { stdout } = await run(python, [fileURLToPath2(new URL("./node_serial.py", import.meta.url)), "--list"], { signal, timeout, maxBuffer: 1024 * 1024, windowsHide: true });
    const ports = JSON.parse(stdout);
    if (!Array.isArray(ports)) throw new Error("Invalid serial list");
    return ports;
  } catch (cause) {
    if (signal?.aborted) throw signal.reason;
    if (cause?.code === "ETIMEDOUT") throw Object.assign(new Error("Serial enumeration timed out"), { code: "TIMEOUT", cause });
    throw Object.assign(new Error("Serial enumeration unavailable: install Python and pyserial, or select --python"), { code: "SERIAL_UNAVAILABLE", cause });
  }
}
function filterSerialPorts(ports, { platform = process.platform, allPorts = false } = {}) {
  const valid = ports.filter((port) => {
    const path = port.path;
    if (typeof path !== "string" || /[\x00-\x1f\x7f]/.test(path)) return false;
    if (platform === "win32") return /^(?:\\\\\.\\)?COM[1-9]\d*$/i.test(path);
    if (platform === "darwin") return /^\/dev\/(?:cu|tty)\.[^/]+$/.test(path);
    if (platform === "linux") return /^\/dev\/[^/]+$/.test(path) && !/^\/dev\/(?:tty\d*|console|ptmx)$/.test(path);
    return false;
  });
  const paths = new Set(valid.map((port) => port.path));
  const seen = /* @__PURE__ */ new Set();
  return valid.filter((port) => {
    const path = port.path;
    if (platform === "darwin" && path.startsWith("/dev/tty.") && paths.has(path.replace("/dev/tty.", "/dev/cu."))) return false;
    const key = platform === "win32" ? path.replace(/^\\\\\.\\/, "").toUpperCase() : path;
    if (seen.has(key)) return false;
    seen.add(key);
    const usb = port.vendorId != null || /\bUSB\b/i.test(port.hwid ?? "");
    const usbName = platform === "linux" ? /^\/dev\/tty(?:ACM|USB|XRUSB)\d+$/.test(path) : platform === "darwin" && /^\/dev\/(?:cu|tty)\.[^/]*usb[^/]*$/i.test(path);
    return allPorts || usb || usbName;
  });
}
function serialEntry(port) {
  const vid = port.vendorId, pid = port.productId;
  const usb = vid !== null && vid !== void 0;
  const kind = vid === 12346 && pid === 4097 ? "usj" : [4292, 6790, 1027, 1659].includes(vid) ? "uart" : vid === 12346 && /esp.vision/i.test(port.product ?? "") ? "usb" : usb ? "serial" : "uart";
  return { interface: kind, address: port.path, status: "unprobed", identity: null, usb: { vendorId: vid ?? null, productId: pid ?? null, serialNumber: port.serialNumber ?? null, product: port.product ?? null, manufacturer: port.manufacturer ?? null }, interfaceSource: "descriptor-candidate" };
}
function transportFor(entry, options2 = {}) {
  return entry.interface === "tcp" ? tcpTransport({ host: entry.host, port: entry.port }) : serialTransport({ serial: entry.address, role: entry.interface, python: options2.python ?? defaultPython });
}
async function inventory(options2 = {}, dependencies = {}) {
  const { signal, timeout = 3e3, probe = false, interfaces = ["all"] } = options2;
  const matches = (kind) => interfaces.includes("all") || interfaces.includes(kind) || kind !== "tcp" && interfaces.includes("serial");
  const warnings = [], rows = [];
  let sourcesAvailable = 0;
  const tasks = [];
  if (interfaces.some((kind) => kind !== "tcp")) tasks.push((async () => {
    try {
      const ports = await (dependencies.listSerial ?? listSerial)({ ...options2, signal });
      rows.push(...filterSerialPorts(ports, { platform: dependencies.platform ?? process.platform, allPorts: options2.allPorts }).map(serialEntry).filter((row) => matches(row.interface)));
      sourcesAvailable++;
    } catch (error2) {
      if (signal?.aborted) throw error2;
      warnings.push({ source: "serial", code: error2.code ?? "SERIAL_UNAVAILABLE", message: "Serial enumeration unavailable; check Python/pyserial and access permissions" });
    }
  })());
  if (matches("tcp")) tasks.push((async () => {
    try {
      const devices = await (dependencies.listNetwork ?? ((request) => createNodeDiscovery().list(request)))({ timeout, signal });
      sourcesAvailable++;
      rows.push(...devices.map((device) => ({ interface: "tcp", address: `${device.addresses[0]}:${device.port}`, host: device.addresses[0], port: device.port, status: "advertised", identity: { deviceId: device.deviceId, hostname: device.hostname, board: device.board, firmwareVersion: device.firmwareVersion }, advertisement: device })));
    } catch (error2) {
      if (signal?.aborted) throw error2;
      warnings.push({ source: "tcp", code: error2.code ?? "DISCOVERY_UNAVAILABLE", message: "LAN discovery unavailable; install multicast-dns and check multicast access" });
    }
  })());
  await Promise.all(tasks);
  signal?.throwIfAborted();
  if (probe) for (const row of rows) {
    signal?.throwIfAborted();
    const device = (dependencies.createDevice ?? createDevice)({ transport: (dependencies.transportFor ?? transportFor)(row, options2) });
    try {
      const result = await device.connect({ role: row.interface === "serial" ? "unknown" : row.interface, timeout: options2.probeTimeout ?? 5e3, signal, probeRepl: false, ...row.advertisement ? { expectedDevice: row.advertisement } : {} });
      row.identity = result.identity;
      row.inspection = await device.inspect({ fields: options2.fields, signal });
      row.status = "identified";
    } catch (error2) {
      if (signal?.aborted) throw error2;
      row.status = error2.code === "SERIAL_ACCESS_DENIED" ? "permission-denied" : error2.code === "SERIAL_BUSY" ? "busy" : "unidentified";
      row.error = { code: error2.code ?? "PROBE_FAILED", message: "Probe failed; the port may be busy, inaccessible, unflashed or running another firmware" };
    } finally {
      await device.disconnect().catch(() => {
        row.cleanupFailed = true;
      });
    }
  }
  const rank = (row) => row.status === "identified" ? 0 : row.status === "advertised" ? 1 : row.status === "unprobed" ? 2 : 3;
  rows.sort((a, b) => rank(a) - rank(b) || a.address.localeCompare(b.address, "en", { numeric: true }));
  const groups = /* @__PURE__ */ new Map();
  for (const [index, row] of rows.entries()) {
    row.number = index + 1;
    const id = row.identity?.deviceId;
    if (id && !groups.has(id)) groups.set(id, groups.size + 1);
    row.group = id ? groups.get(id) : null;
  }
  return { devices: rows, warnings, sourcesAvailable };
}

// node_modules/@esp-vision/device-core/src/node_rom.js
function openNodeRom({ port, python = defaultPython, signal } = {}) {
  if (!port) throw new TypeError("Firmware update requires a local --port");
  let child, input, pending, sequence = 0, closed = false;
  const fail2 = (code) => Object.assign(new Error(code === "ESPTOOL_UNAVAILABLE" ? "Install Python esptool>=5.3,<6 for the built-in flasher" : "ROM operation failed"), { code });
  const reject = (code) => {
    if (pending) {
      clearTimeout(pending.timer);
      pending.reject(fail2(code));
      pending = null;
    }
  };
  function rpc(method, args = []) {
    if (closed) return Promise.reject(fail2("ROM_CLOSED"));
    if (pending) return Promise.reject(fail2("ROM_BUSY"));
    return new Promise((resolve2, rejectPromise) => {
      const id = ++sequence;
      pending = { id, resolve: resolve2, reject: rejectPromise, timer: setTimeout(() => {
        reject("ROM_TIMEOUT");
        void loader.disconnect();
      }, 18e4) };
      child.stdin.write(JSON.stringify({ id, method, args }) + "\n", (error2) => {
        if (error2) reject("ROM_IO_FAILED");
      });
    });
  }
  const loader = {
    async initialize() {
      signal?.throwIfAborted();
      child = spawn2(python, ["-u", fileURLToPath3(new URL("./node_rom.py", import.meta.url)), port], { stdio: ["pipe", "pipe", "ignore"], windowsHide: true });
      child.on("error", () => reject("ESPTOOL_UNAVAILABLE"));
      child.on("exit", () => reject("ROM_CLOSED"));
      child.stdin.on("error", () => reject("ROM_IO_FAILED"));
      input = createInterface({ input: child.stdout });
      input.on("line", (line) => {
        try {
          const message = JSON.parse(line);
          if (message.error && !message.id) return reject(message.error);
          if (!pending || message.id !== pending.id) return;
          const operation = pending;
          pending = null;
          clearTimeout(operation.timer);
          if (message.error) operation.reject(Object.assign(fail2(message.error), { operation: message.method, cause: message.detail }));
          else operation.resolve(message.result);
        } catch {
          reject("ROM_RESPONSE_INVALID");
        }
      });
      const cancelled = () => {
        reject("CANCELLED");
        void loader.disconnect();
      };
      signal?.addEventListener("abort", cancelled, { once: true });
      try {
        Object.assign(loader, await rpc("initialize"));
      } finally {
        signal?.removeEventListener("abort", cancelled);
      }
    },
    flashId: () => rpc("flashId"),
    getSecurityInfo: () => rpc("security"),
    async runStub() {
      await rpc("stub");
      return loader;
    },
    async readFlash(offset, bytes) {
      return new Uint8Array(Buffer.from(await rpc("read", [offset, bytes]), "base64"));
    },
    async flashData(bytes, progress, offset) {
      await rpc("write", [offset, Buffer.from(bytes).toString("base64")]);
      progress(bytes.byteLength, bytes.byteLength);
    },
    readRegister: (address) => rpc("readRegister", [address]),
    writeRegister: (address, value, mask) => rpc("writeRegister", [address, value, mask]),
    hardReset: () => rpc("reset"),
    async disconnect() {
      if (closed) return;
      closed = true;
      reject("ROM_CLOSED");
      input?.close();
      if (!child || child.exitCode !== null) return;
      await new Promise((resolve2) => {
        const timer = setTimeout(() => {
          child.kill();
          resolve2();
        }, 2e3);
        child.once("exit", () => {
          clearTimeout(timer);
          resolve2();
        });
        child.stdin.end();
      });
    }
  };
  return loader;
}

// src/cli.js
var MAX_FILE_OUTPUT = 16 * 1024 * 1024;
var DEFAULT_PYTHON_OUTPUT = 16 * 1024;
var MAX_PYTHON_OUTPUT = 1024 * 1024;
var MAX_BATCH_OPERATIONS = 100;
var schemaVersion = 1;
var fields = ["identity", "capabilities", "runtime", "network", "storage"];
var usage = `esp-vision-device inspect [--port PATH | --tcp HOST[:PORT] | --select N]
  [--fields identity,capabilities,runtime,network,storage] [--probe]
  [--interface all|serial|usb|usj|uart|tcp] [--all-ports] [--json]
esp-vision-device configure (--port PATH | --tcp HOST[:PORT])
  [--ssid SSID [--password-stdin]] [--forget-wifi] [--network-enabled true|false]
esp-vision-device control (--port PATH | --tcp HOST[:PORT])
  --action stop|bootloader
esp-vision-device control (--port PATH | --tcp HOST[:PORT]) --action reset --mode soft|hard
esp-vision-device firmware check [--port PATH | --tcp HOST[:PORT]]
  [--catalog FILE|HTTPS_URL] [--board BOARD --current-version VERSION] [--version VERSION] [--mode update|install]
esp-vision-device firmware update [--port PATH | --tcp HOST[:PORT]]
  [--catalog FILE|HTTPS_URL] --version VERSION [--image FIRMWARE.bin] [--mode update|install]
  [--board BOARD --current-version VERSION]
esp-vision-device python (--source CODE | --file LOCAL.py | --path DEVICE.py)
  [--completion wait|start] [--timeout MS] [--max-output-chars N] [--port PATH | --tcp HOST[:PORT]]
esp-vision-device files list [--path DEVICE_DIR] [--recursive]
esp-vision-device files read DEVICE_PATH --output LOCAL_FILE [--max-bytes N]
esp-vision-device files write DEVICE_PATH --file LOCAL_FILE [--no-overwrite]
esp-vision-device files remove DEVICE_PATH [--type file|directory]
esp-vision-device files mkdir DEVICE_DIR [--recursive]
esp-vision-device capture camera|screen --output LOCAL.jpg [--quality N] [--max-bytes N]
  camera: Observe the application's camera-frame source, not the LCD image. Freshness and application drawing depend on firmware publication behavior.
  screen: Capture the current LCD framebuffer, including drawing rendered there. Use this to verify LCD overlays and UI; display initialization is required.
esp-vision-device batch PLAN.json [--port PATH | --tcp HOST[:PORT]]
esp-vision-device watch --duration MS [--port PATH | --tcp HOST[:PORT]]
Common: --timeout MS, --python PYTHON (default python3; Windows python), --json, --help
Serial setup: check PYTHON --version and PYTHON -c "import serial" with the selected interpreter. Install pyserial there with PYTHON -m pip install pyserial. Windows Launcher: --python py and py -m pip install pyserial.
All commands that operate on a device require --port or --tcp, except inspect and offline firmware check.
Python --completion start accepts only --path DEVICE.py. It acknowledges the start, disconnects, and exits; it does not retain a daemon or resumable job.
Python --timeout is an execution deadline for --completion wait only; omit it with --completion start.
Control --mode applies only to --action reset; omit it with stop or bootloader.
While an application is running, use passive inspect/capture/watch or native file uploads. Python and files list/read/remove/mkdir use the REPL and can interrupt it.
Verify a started app with passive captures before stopping it and reading progress files. Start acknowledgement is not application readiness; runtime.scriptRunning is local to the current session.
Batch plans use schemaVersion 1 with an operations array. Operations run sequentially over one connection and stop at the first failure.
In JSON mode stdout contains one schemaVersion 1 JSON envelope. Python output, status, logs, and errors are NDJSON events on stderr.
Binary file reads and JPEG captures always write to --output. Local output is capped at 16 MiB by default and --max-bytes may lower that cap.
Firmware versions come from dl.espressif.com by default; local catalogs are advanced overrides.
Firmware update uses the built-in serial flasher (Python esptool==5.6.0). TCP is not OTA.
Default mode update preserves the existing layout/data; explicit mode install writes a complete image, replacing data in its written range. Blank boards require --board and a ROM-capable USJ/UART port, not an application USB-OTG interface.`;
var cliCapabilities = Object.freeze({
  commands: {
    inspect: ["device discovery", "identity, capability, runtime, network and storage inspection"],
    configure: ["Wi-Fi credentials and network enablement"],
    control: ["stop", "soft reset", "hard reset", "bootloader handoff"],
    firmware: ["check", "update"],
    python: ["--source CODE", "--file LOCAL.py", "--path DEVICE.py", "live output, log and state NDJSON events"],
    files: ["list", "read", "write", "remove", "mkdir"],
    capture: ["camera JPEG: latest application camera frame, not the LCD image; drawing depends on firmware publication behavior", "screen JPEG: LCD framebuffer with drawing rendered there; requires display initialization"],
    batch: ["sequential schemaVersion 1 JSON plan", "one connection", "stop at first failure"],
    watch: ["bounded output, log, state and diagnostic stream", "one connection", "no script launch or reconnect"]
  },
  output: {
    json: "One schemaVersion 1 envelope on stdout",
    events: "NDJSON on stderr",
    binary: "Local files only; never embedded in JSON",
    pythonOutput: "Live python.output NDJSON on stderr, capped at maxOutputChars (default 16384); one truncated marker when capped",
    pythonLogAndState: "Live python.log and python.state NDJSON on stderr during Python execution"
  },
  limits: { localFileBytes: MAX_FILE_OUTPUT, pythonOutputCharsDefault: DEFAULT_PYTHON_OUTPUT, pythonOutputCharsMax: MAX_PYTHON_OUTPUT, batchOperations: MAX_BATCH_OPERATIONS, watchDurationMs: { min: 1, max: 36e5 } },
  exitCodes: { success: 0, failure: 1, argumentOrPlan: 2, sigint: 130, sigterm: 143 }
});
var error = (code, message, options2 = {}) => Object.assign(new Error(message), { code, ...options2 });
var optionError = (message) => error("ARGUMENT", message);
var knownDeviceCommands = ["configure", "control", "firmware", "python", "files", "capture", "batch", "watch"];
var commonOptions = ["port", "tcp", "python", "timeout", "json", "role"];
function devicePath(value, { root = false, fail: fail2 = optionError } = {}) {
  if (typeof value !== "string" || !value.startsWith("/") || !root && value === "/" || new TextEncoder().encode(value).length > 123 || /[\x00-\x1f\x7f\\"]/.test(value) || value.includes("..") || value.includes("//") || value.length > 1 && value.endsWith("/")) {
    const shellHint = typeof value === "string" && /^[A-Za-z]:[\\/]/.test(value) ? ' Received a Windows host path; Git Bash/MSYS may have converted the device path. Use PowerShell or prefix this command with MSYS2_ARG_CONV_EXCL="*" and keep local paths in Windows form.' : "";
    throw fail2("Expected an absolute device path (for example /models), at most 123 UTF-8 bytes, without traversal, trailing slash or forbidden characters." + shellHint);
  }
  return value;
}
function parseTcpAddress(value) {
  const match = /^(?:\[([0-9a-fA-F:]+)\]|([^\s:/@?#]+))(?::([0-9]+))?$/.exec(value);
  if (!match || Number(match[3] ?? 3232) < 1 || Number(match[3] ?? 3232) > 65535) {
    throw optionError("Expected TCP host[:port] without credentials or URL");
  }
  return { interface: "tcp", host: match[1] ?? match[2], port: Number(match[3] ?? 3232), address: value };
}
function parsePositiveInteger(value, label, { max = Number.MAX_SAFE_INTEGER } = {}) {
  if (!/^\d+$/.test(String(value))) throw optionError(`${label} must be a positive integer`);
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < 1 || number > max) throw optionError(`${label} must be 1..${max}`);
  return number;
}
function parseCommandOptions(args, strict = true) {
  const booleans = [
    "help",
    "json",
    "all-ports",
    "probe",
    "forget-wifi",
    "password-stdin",
    "recursive",
    "no-overwrite"
  ];
  const strings = [
    "port",
    "tcp",
    "select",
    "fields",
    "interface",
    "python",
    "timeout",
    "probe-timeout",
    "role",
    "ssid",
    "network-enabled",
    "action",
    "mode",
    "catalog",
    "board",
    "current-version",
    "version",
    "image",
    "source",
    "file",
    "path",
    "completion",
    "max-output-chars",
    "output",
    "max-bytes",
    "quality",
    "type",
    "duration"
  ];
  try {
    return parseArgs({
      args,
      strict,
      allowPositionals: true,
      options: Object.fromEntries([
        ...booleans.map((key) => [key, { type: "boolean" }]),
        ...strings.map((key) => [key, { type: "string" }])
      ])
    });
  } catch (cause) {
    throw error("ARGUMENT", cause.message, { cause });
  }
}
function parseCli(args) {
  const { values: v, positionals: p } = parseCommandOptions(args);
  if (v.help) return { help: true, json: v.json ?? false };
  const command = p[0] ?? "inspect";
  const subcommand = command === "firmware" || command === "files" ? p[1] : null;
  const allowedCommands = ["inspect", ...knownDeviceCommands];
  if (!allowedCommands.includes(command)) throw optionError("Unknown command; use --help");
  const expectedPositionals = {
    inspect: 1,
    configure: 1,
    control: 1,
    firmware: 2,
    python: 1,
    files: 3,
    capture: 2,
    batch: 2,
    watch: 1
  }[command];
  if (p.length > expectedPositionals) throw optionError("Unexpected positional argument");
  if (command === "firmware" && !["check", "update"].includes(subcommand) || command === "files" && !["list", "read", "write", "remove", "mkdir"].includes(subcommand)) {
    throw optionError(`Unknown ${command} operation; use --help`);
  }
  const allowed = {
    inspect: ["all-ports", "select", "fields", "interface", "probe", "probe-timeout"],
    configure: ["ssid", "forget-wifi", "password-stdin", "network-enabled"],
    control: ["action", "mode"],
    firmware: ["mode", "catalog", "board", "current-version", "version", "image"],
    python: ["source", "file", "path", "completion", "max-output-chars"],
    files: subcommand === "list" ? ["path", "recursive"] : subcommand === "read" ? ["output", "max-bytes"] : subcommand === "write" ? ["file", "no-overwrite"] : subcommand === "remove" ? ["type"] : ["recursive"],
    capture: ["output", "quality", "max-bytes"],
    batch: [],
    watch: ["duration"]
  }[command];
  for (const key of Object.keys(v)) {
    if (!["help", ...commonOptions, ...allowed].includes(key)) {
      throw optionError(`Option --${key} is not valid for ${command}${subcommand ? ` ${subcommand}` : ""}`);
    }
  }
  const endpointCount = [v.port, v.tcp].filter((value) => value !== void 0).length;
  if (endpointCount > 1) throw optionError("Select exactly one device address");
  if (v.role && !["usb", "usj", "uart", "unknown"].includes(v.role)) throw optionError("Invalid serial role");
  if (v.role && !v.port) throw optionError("--role requires --port");
  const endpoint = v.tcp ? parseTcpAddress(v.tcp) : v.port ? { interface: v.role ?? "unknown", address: v.port } : void 0;
  const explicitTimeout = v.timeout !== void 0;
  const timeout = explicitTimeout ? parsePositiveInteger(v.timeout, "Timeout", { max: 6e5 }) : command === "inspect" && !endpoint && !v.select ? 3e3 : 3e4;
  const probeTimeout = parsePositiveInteger(v["probe-timeout"] ?? "5000", "Probe timeout", { max: 6e4 });
  const python = v.python ?? defaultPython;
  const options2 = { ...v, command, subcommand, endpoint, timeout, timeoutExplicit: explicitTimeout, connectTimeout: 3e4, probeTimeout, python };
  if (command === "inspect") {
    options2.allPorts = v["all-ports"] ?? false;
    options2.interfaces = (v.interface ?? "all").split(",");
    if (options2.interfaces.some((value) => !["all", "serial", "usb", "usj", "uart", "tcp"].includes(value))) throw optionError("Unknown interface filter");
    options2.fields = v.fields?.split(",");
    if (options2.fields?.some((value) => !fields.includes(value))) throw optionError("Unknown inspect field");
    if (options2.fields && !endpoint && !v.probe && !v.select) throw optionError("--fields requires a target, --select or --probe");
    if (v.select !== void 0) {
      if (!/^\d+$/.test(v.select) || Number(v.select) < 1) throw optionError("--select must be a positive result number");
      options2.select = Number(v.select);
    }
  }
  if (command === "configure") {
    if (!endpoint) throw optionError("Specify --port or --tcp");
    if (v["network-enabled"] !== void 0 && !["true", "false"].includes(v["network-enabled"])) throw optionError("--network-enabled must be true or false");
    if (v.ssid && v["forget-wifi"] || v["password-stdin"] && !v.ssid || !v.ssid && !v["forget-wifi"] && v["network-enabled"] === void 0) {
      throw optionError("Specify --ssid, --forget-wifi or --network-enabled");
    }
  }
  if (command === "control") {
    if (!endpoint) throw optionError("Specify --port or --tcp");
    if (!["stop", "reset", "bootloader"].includes(v.action)) throw optionError("--action must be stop, reset or bootloader");
    if (v.action === "reset" && !["soft", "hard"].includes(v.mode)) throw optionError("--action reset requires --mode soft or hard");
    if (v.action !== "reset" && v.mode !== void 0) throw optionError("--mode applies only to --action reset; omit it with stop or bootloader");
  }
  if (command === "firmware") {
    if (v.mode !== void 0 && !["update", "install"].includes(v.mode)) throw optionError("Firmware mode must be update or install");
    if (v.mode === "install" && !v.board) throw optionError("Firmware installation requires explicit --board");
    if (!endpoint && !v.board) throw optionError("Firmware requires a connected device or --board");
    if (subcommand === "update" && (!v.port || !v.version)) throw optionError("Firmware update requires local --port and explicit --version");
    if (subcommand === "check" && v.image) throw optionError("--image applies only to firmware update");
  }
  if (command === "python") {
    if (!endpoint) throw optionError("Specify --port or --tcp");
    const forms = ["source", "file", "path"].filter((key) => v[key] !== void 0);
    if (forms.length !== 1) throw optionError("Specify exactly one of --source, --file or --path");
    if (v.path !== void 0) devicePath(v.path);
    options2.completion = v.completion ?? "wait";
    if (!["wait", "start"].includes(options2.completion)) throw optionError("--completion must be wait or start");
    if (options2.completion === "start" && v.path === void 0) throw optionError("--completion start requires device --path");
    if (options2.completion === "start" && explicitTimeout) throw optionError("--timeout applies only with --completion wait");
    options2.maxOutputChars = parsePositiveInteger(v["max-output-chars"] ?? String(DEFAULT_PYTHON_OUTPUT), "--max-output-chars", { max: MAX_PYTHON_OUTPUT });
  }
  if (command === "files" || command === "capture" || command === "batch" || command === "watch") {
    if (!endpoint) throw optionError("Specify --port or --tcp");
  }
  if (command === "watch") {
    if (v.duration === void 0) throw optionError("watch requires --duration MS");
    options2.duration = parsePositiveInteger(v.duration, "Watch duration", { max: 36e5 });
  }
  if (command === "files") {
    const pathPositional = p[2];
    if (subcommand === "list") {
      if (pathPositional !== void 0) throw optionError("files list accepts --path DEVICE_DIR");
      options2.path = v.path ?? "/";
    } else {
      if (!pathPositional) throw optionError(`files ${subcommand} requires DEVICE_PATH`);
      if (v.path !== void 0) throw optionError(`files ${subcommand} uses a positional device path`);
      options2.path = pathPositional;
    }
    devicePath(options2.path, { root: subcommand === "list" });
    if (subcommand === "read") {
      if (!v.output) throw optionError("files read requires --output LOCAL_FILE");
      options2.maxBytes = parsePositiveInteger(v["max-bytes"] ?? String(MAX_FILE_OUTPUT), "--max-bytes", { max: MAX_FILE_OUTPUT });
    }
    if (subcommand === "write" && !v.file) throw optionError("files write requires --file LOCAL_FILE");
    if (subcommand === "remove" && v.type !== void 0 && !["file", "directory"].includes(v.type)) throw optionError("--type must be file or directory");
  }
  if (command === "capture") {
    options2.source = p[1];
    if (!["camera", "screen"].includes(options2.source)) throw optionError("Capture source must be camera or screen");
    if (!v.output) throw optionError("capture requires --output LOCAL.jpg");
    options2.maxBytes = parsePositiveInteger(v["max-bytes"] ?? String(MAX_FILE_OUTPUT), "--max-bytes", { max: MAX_FILE_OUTPUT });
    if (v.quality !== void 0) options2.quality = parsePositiveInteger(v.quality, "--quality", { max: 100 });
    if (options2.quality !== void 0 && options2.quality < 1) throw optionError("--quality must be 1..100");
  }
  if (command === "batch") {
    if (!p[1]) throw optionError("batch requires PLAN.json");
    options2.planFile = resolve(p[1]);
  }
  if (command === "inspect" && endpoint && v.select !== void 0) throw optionError("Use either an explicit device or --select");
  if (command === "inspect" && v.role && !v.port) throw optionError("--role requires --port");
  return options2;
}
async function passwordFromInput(options2) {
  if (options2["password-stdin"]) {
    let value = "";
    for await (const chunk of process.stdin) {
      value += chunk;
      if (value.length > 4096) throw optionError("Password input is too long");
    }
    return value.replace(/\r?\n$/, "");
  }
  if (!process.stdin.isTTY) throw optionError("Use --password-stdin for non-interactive Wi-Fi configuration");
  process.stderr.write("Wi-Fi password (hidden; empty for open network): ");
  const output = new Writable({ write(_chunk, _encoding, callback) {
    callback();
  } });
  const terminal = createInterface2({ input: process.stdin, output, terminal: true });
  terminal.once("SIGINT", () => process.kill(process.pid, "SIGINT"));
  try {
    return await terminal.question("", { signal: options2.signal });
  } finally {
    terminal.close();
    process.stderr.write("\n");
  }
}
function errorInfo(failure3) {
  if (!failure3) return void 0;
  const info = { code: failure3.code ?? "COMMAND_FAILED", message: failure3.message ?? "Command failed" };
  if (failure3.code === "ROM_OPERATION_FAILED") {
    if (typeof failure3.operation === "string") info.operation = failure3.operation.slice(0, 64);
    if (typeof failure3.cause === "string") info.detail = failure3.cause.slice(0, 1024);
  }
  if (failure3.reset?.acknowledged === false && failure3.reset.outcome === "unknown") {
    info.reset = { acknowledged: false, outcome: "unknown" };
  }
  if (String(failure3.code).startsWith("ROM_") && typeof failure3.transition?.command?.attempted === "boolean") {
    const transition = failure3.transition;
    info.transition = {
      command: {
        attempted: transition.command.attempted,
        acknowledged: transition.command.acknowledged === true,
        outcome: ["unknown", "not_attempted"].includes(transition.command.outcome) ? transition.command.outcome : "unknown"
      },
      observed: transition.observed === "rom" ? "rom" : null,
      cleanup: typeof transition.cleanup?.ok === "boolean" ? { ok: transition.cleanup.ok } : null
    };
  }
  return info;
}
function attachCleanupFailure(primary, cleanupFailure) {
  if (primary && cleanupFailure) {
    primary.cleanupError = errorInfo(cleanupFailure);
    return primary;
  }
  return primary ?? cleanupFailure;
}
function validatePlan(plan, planFile) {
  const allowedOps = /* @__PURE__ */ new Set(["python", "files.list", "files.read", "files.write", "files.remove", "files.mkdir", "capture"]);
  const planError = (message) => error("INVALID_PLAN", message);
  if (!plan || typeof plan !== "object" || Array.isArray(plan) || plan.schemaVersion !== schemaVersion || !Array.isArray(plan.operations) || plan.operations.length < 1 || plan.operations.length > MAX_BATCH_OPERATIONS || Object.keys(plan).some((key) => !["schemaVersion", "operations"].includes(key))) {
    throw planError("Batch plan must be an object with schemaVersion 1 and 1..100 operations");
  }
  const base = dirname(planFile);
  const local = (value) => {
    if (typeof value !== "string" || value.length === 0 || value.includes("\0")) throw planError("Batch local paths must be nonempty strings");
    return resolve(base, value);
  };
  const planDevicePath = (value, options2 = {}) => devicePath(value, { ...options2, fail: planError });
  return plan.operations.map((operation, index) => {
    const fail2 = (message) => {
      throw planError(`Batch operation ${index + 1}: ${message}`);
    };
    if (!operation || typeof operation !== "object" || Array.isArray(operation) || typeof operation.op !== "string" || !allowedOps.has(operation.op)) fail2("unknown or malformed operation");
    const allowed = {
      python: ["op", "source", "file", "path"],
      "files.list": ["op", "path", "recursive"],
      "files.read": ["op", "path", "output", "maxBytes"],
      "files.write": ["op", "path", "file", "overwrite"],
      "files.remove": ["op", "path", "type"],
      "files.mkdir": ["op", "path", "recursive"],
      capture: ["op", "source", "output", "quality", "maxBytes"]
    }[operation.op];
    if (Object.keys(operation).some((key) => !allowed.includes(key))) fail2("contains an unknown field");
    const copy = { ...operation };
    if (operation.op === "python") {
      const forms = ["source", "file", "path"].filter((key) => Object.hasOwn(operation, key));
      if (forms.length !== 1) fail2("python requires exactly one of source, file or path");
      if (operation.source !== void 0 && typeof operation.source !== "string") fail2("source must be a string");
      if (operation.path !== void 0) copy.path = planDevicePath(operation.path);
      if (operation.file !== void 0) copy.file = local(operation.file);
    } else if (operation.op === "files.list") {
      copy.path = planDevicePath(operation.path ?? "/", { root: true });
      if (operation.recursive !== void 0 && typeof operation.recursive !== "boolean") fail2("recursive must be boolean");
    } else if (operation.op === "files.read") {
      copy.path = planDevicePath(operation.path);
      if (operation.output === void 0) fail2("files.read requires output");
      copy.output = local(operation.output);
      copy.maxBytes = operation.maxBytes ?? MAX_FILE_OUTPUT;
      if (!Number.isSafeInteger(copy.maxBytes) || copy.maxBytes < 1 || copy.maxBytes > MAX_FILE_OUTPUT) fail2("maxBytes must be 1..16 MiB");
    } else if (operation.op === "files.write") {
      copy.path = planDevicePath(operation.path);
      if (operation.file === void 0) fail2("files.write requires file");
      copy.file = local(operation.file);
      if (operation.overwrite !== void 0 && typeof operation.overwrite !== "boolean") fail2("overwrite must be boolean");
    } else if (operation.op === "files.remove") {
      copy.path = planDevicePath(operation.path);
      if (operation.type !== void 0 && !["file", "directory"].includes(operation.type)) fail2("type must be file or directory");
    } else if (operation.op === "files.mkdir") {
      copy.path = planDevicePath(operation.path);
      if (operation.recursive !== void 0 && typeof operation.recursive !== "boolean") fail2("recursive must be boolean");
    } else if (operation.op === "capture") {
      if (!["camera", "screen"].includes(operation.source)) fail2("capture source must be camera or screen");
      if (operation.output === void 0) fail2("capture requires output");
      copy.output = local(operation.output);
      copy.maxBytes = operation.maxBytes ?? MAX_FILE_OUTPUT;
      if (!Number.isSafeInteger(copy.maxBytes) || copy.maxBytes < 1 || copy.maxBytes > MAX_FILE_OUTPUT) fail2("maxBytes must be 1..16 MiB");
      if (operation.quality !== void 0 && (!Number.isSafeInteger(operation.quality) || operation.quality < 1 || operation.quality > 100)) fail2("quality must be 1..100");
    }
    return copy;
  });
}
async function loadPlan(options2, dependencies) {
  const read = dependencies.readFile ?? readFile;
  let plan;
  try {
    plan = JSON.parse(await read(options2.planFile, "utf8"));
  } catch (cause) {
    if (cause.code === "ARGUMENT") throw cause;
    throw error("INVALID_PLAN", `Cannot read batch plan: ${cause.message}`, { cause });
  }
  return validatePlan(plan, options2.planFile);
}
function emit(dependencies, event) {
  dependencies.onEvent?.({ schemaVersion, ...event });
}
async function writeLocalOutput(path, data, maxBytes, dependencies) {
  if (!(data instanceof Uint8Array)) throw error("INVALID_DEVICE_RESULT", "Device returned no binary data");
  if (data.byteLength > maxBytes) throw error("OUTPUT_TOO_LARGE", `Output exceeds ${maxBytes} bytes`);
  await (dependencies.writeFile ?? writeFile)(path, data);
  return { output: path, bytes: data.byteLength };
}
function createPythonObserver(device, request, dependencies) {
  const maxOutputChars = request.maxOutputChars ?? DEFAULT_PYTHON_OUTPUT;
  const unsubscribers = [];
  let outputChars = 0;
  let liveOutputSeen = false;
  let truncationReported = false;
  let closed = false;
  const reportTruncated = () => {
    if (truncationReported) return;
    truncationReported = true;
    emit(dependencies, { event: "python.output", data: "", truncated: true, maxOutputChars });
  };
  const output = (text, source = "live") => {
    if (source === "live") liveOutputSeen = true;
    if (typeof text !== "string" || text.length === 0) return;
    const remaining = Math.max(0, maxOutputChars - outputChars);
    let bounded = text.slice(0, remaining);
    if (bounded.length && /[\uD800-\uDBFF]/.test(bounded.at(-1))) bounded = bounded.slice(0, -1);
    if (bounded) {
      outputChars += bounded.length;
      emit(dependencies, { event: "python.output", data: bounded, truncated: false });
    }
    if (bounded.length < text.length) reportTruncated();
  };
  const close = () => {
    if (closed) return;
    closed = true;
    for (const unsubscribe of unsubscribers.splice(0)) {
      try {
        unsubscribe?.();
      } catch {
      }
    }
  };
  if (typeof device.on === "function") {
    try {
      unsubscribers.push(device.on("python.output", (text) => output(text)));
      unsubscribers.push(device.on("log", (text) => emit(dependencies, { event: "python.log", data: text })));
      unsubscribers.push(device.on("state", (state) => emit(dependencies, { event: "python.state", data: state })));
    } catch (failure3) {
      close();
      throw failure3;
    }
  }
  return {
    close,
    output(text) {
      output(text, "fallback");
    },
    reportTruncated,
    get liveOutputSeen() {
      return liveOutputSeen;
    },
    get outputChars() {
      return outputChars;
    }
  };
}
async function runPython(device, request, dependencies) {
  const startedAt = Date.now();
  const observer = createPythonObserver(device, request, dependencies);
  let result;
  try {
    result = await device.python.execute({
      ...request,
      ...dependencies.signal ? { signal: dependencies.signal } : {},
      maxOutputChars: request.maxOutputChars ?? DEFAULT_PYTHON_OUTPUT
    });
  } finally {
    observer.close();
  }
  const durationMs = Date.now() - startedAt;
  if (!observer.liveOutputSeen && result.output) observer.output(result.output);
  if (result.outputTruncated) observer.reportTruncated();
  if (request.completion === "start") {
    if (result.done && typeof result.done.then === "function") {
      Promise.resolve(result.done).catch(() => {
      });
    }
    return { ok: true, started: true, path: result.path ?? request.path, durationMs };
  }
  const { output, ...metadata } = result;
  const summary = { ...metadata, outputChars: observer.outputChars, durationMs };
  if (result.ok === false) throw error("PYTHON_FAILED", "Python execution failed", { result: summary });
  return summary;
}
async function runOperation(device, operation, options2, dependencies) {
  const signal = dependencies.signal;
  if (operation.op === "python") {
    const request = {
      ...operation.source !== void 0 ? { source: operation.source } : {},
      ...operation.path !== void 0 ? { path: operation.path } : {},
      ...operation.file !== void 0 ? { source: await (dependencies.readFile ?? readFile)(operation.file, "utf8") } : {},
      completion: "wait",
      maxOutputChars: DEFAULT_PYTHON_OUTPUT,
      ...options2.timeoutExplicit ? { timeout: options2.timeout } : {}
    };
    return runPython(device, request, dependencies);
  }
  if (operation.op === "files.list") return device.files.list({ path: operation.path ?? "/", recursive: operation.recursive ?? false, signal });
  if (operation.op === "files.read") {
    const data = await device.files.read({ path: operation.path, maxBytes: operation.maxBytes ?? MAX_FILE_OUTPUT, ...options2.timeoutExplicit ? { timeout: options2.timeout } : {}, signal });
    return { path: operation.path, ...await writeLocalOutput(operation.output, data, operation.maxBytes ?? MAX_FILE_OUTPUT, dependencies) };
  }
  if (operation.op === "files.write") {
    const data = await (dependencies.readFile ?? readFile)(operation.file);
    return device.files.write({ path: operation.path, data, overwrite: operation.overwrite ?? true, signal });
  }
  if (operation.op === "files.remove") return device.files.remove({ path: operation.path, type: operation.type ?? "file", signal });
  if (operation.op === "files.mkdir") return device.files.mkdir({ path: operation.path, recursive: operation.recursive ?? false, signal });
  if (operation.op === "capture") {
    const capture = await device.capture({ source: operation.source, format: "jpeg", ...operation.quality ? { quality: operation.quality } : {}, ...options2.timeoutExplicit ? { timeout: options2.timeout } : {}, signal });
    const saved = await writeLocalOutput(operation.output, capture.data, operation.maxBytes ?? MAX_FILE_OUTPUT, dependencies);
    return { source: operation.source, mimeType: capture.mimeType ?? "image/jpeg", metadata: capture.metadata ?? null, ...saved };
  }
  throw error("INVALID_PLAN", "Unknown batch operation");
}
async function runBatch(device, options2, plan, dependencies) {
  const completed = [];
  for (let index = 0; index < plan.length; index++) {
    const operation = plan[index];
    emit(dependencies, { event: "batch.operation", state: "started", index: index + 1, op: operation.op });
    try {
      const result = await runOperation(device, operation, options2, dependencies);
      if (result?.ok === false) throw error("PYTHON_FAILED", "Python execution failed", { result });
      completed.push({ index: index + 1, operation: operation.op, result });
      emit(dependencies, { event: "batch.operation", state: "completed", index: index + 1, op: operation.op });
    } catch (failure3) {
      const report = {
        schemaVersion,
        ok: false,
        command: "batch",
        completed,
        failed: { index: index + 1, operation: operation.op, error: errorInfo(failure3) }
      };
      throw error(failure3.code ?? "BATCH_FAILED", failure3.message ?? "Batch operation failed", { batchReport: report, cause: failure3 });
    }
  }
  return { schemaVersion, ok: true, command: "batch", completed };
}
function shouldProbeRepl(options2) {
  if (["inspect", "configure", "capture", "watch"].includes(options2.command)) return false;
  if (options2.command === "files" && options2.subcommand === "write") return false;
  if (options2.command === "firmware" && options2.subcommand === "check") return false;
  return true;
}
function createWatchObserver(device, options2, dependencies) {
  if (typeof device.on !== "function") throw error("EVENTS_UNAVAILABLE", "Device Core does not expose event subscriptions");
  let eventCount = 0;
  let ready = false;
  let finished = false;
  let lost;
  let timer;
  let rejectWait;
  let abortHandler;
  const unsubscribers = [];
  const report = (name, data) => {
    if (finished) return;
    eventCount++;
    emit(dependencies, { event: `watch.${name}`, data });
  };
  const subscribe = (name, handler) => unsubscribers.push(device.on(name, handler));
  subscribe("python.output", (data) => report("output", data));
  subscribe("log", (data) => report("log", data));
  subscribe("state", (state) => {
    report("state", state);
    if (state?.state === "ready") ready = true;
    else if (state?.state === "disconnected" && ready && !finished) {
      lost = error("SESSION_LOST", "Device connection was lost during watch");
      rejectWait?.(lost);
    }
  });
  subscribe("diagnostic", (data) => report("diagnostic", data));
  function close() {
    if (finished) return;
    finished = true;
    clearTimeout(timer);
    if (abortHandler) dependencies.signal?.removeEventListener("abort", abortHandler);
    for (const unsubscribe of unsubscribers.splice(0)) unsubscribe?.();
  }
  return {
    close,
    async wait() {
      if (lost) throw lost;
      const startedAt = Date.now();
      let cancelled = false;
      try {
        await new Promise((resolve2, reject) => {
          rejectWait = reject;
          timer = setTimeout(resolve2, options2.duration);
          abortHandler = () => {
            cancelled = true;
            resolve2();
          };
          dependencies.signal?.addEventListener("abort", abortHandler, { once: true });
          if (dependencies.signal?.aborted) abortHandler();
          if (lost) reject(lost);
        });
      } finally {
        close();
      }
      return { durationMs: Date.now() - startedAt, eventCount, ...cancelled ? { cancelled: true } : {} };
    }
  };
}
async function cliInventory(options2, dependencies) {
  let serialFailure;
  const listing = await inventory(options2, {
    ...dependencies,
    async listSerial(request) {
      try {
        return await (dependencies.listSerial ?? listSerial)(request);
      } catch (failure3) {
        serialFailure = await explainSerialFailure(failure3, options2, dependencies);
        throw serialFailure;
      }
    }
  });
  if (serialFailure) for (const warning of listing.warnings) {
    if (warning.source === "serial") warning.message = serialFailure.message;
  }
  return listing;
}
async function runCli(options2, dependencies = {}) {
  if (options2.help) return { help: usage };
  const startedAt = Date.now();
  let endpoint = options2.endpoint;
  let plan;
  if (options2.command === "batch") {
    try {
      plan = await loadPlan(options2, dependencies);
    } catch (failure3) {
      emit(dependencies, { event: "duration", milliseconds: Date.now() - startedAt });
      throw failure3;
    }
  }
  if (options2.command === "inspect" && !endpoint && !options2.select) {
    const listing = await (dependencies.inventory ?? cliInventory)({ ...options2, signal: dependencies.signal, timeout: Math.min(options2.timeout, 1e4) }, dependencies);
    if (listing.sourcesAvailable === 0) throw error("ENUMERATION_UNAVAILABLE", `No inventory source succeeded. ${listing.warnings.map((warning) => warning.message).join(" ")}`);
    emit(dependencies, { event: "duration", milliseconds: Date.now() - startedAt });
    return listing;
  }
  if (options2.command === "inspect" && !endpoint && options2.select) {
    const listing = await (dependencies.inventory ?? cliInventory)({ ...options2, signal: dependencies.signal, timeout: Math.min(options2.timeout, 1e4) }, dependencies);
    endpoint = listing.devices.find((row) => row.number === options2.select);
    if (!endpoint) {
      emit(dependencies, { event: "duration", milliseconds: Date.now() - startedAt });
      throw error("DEVICE_NOT_FOUND", "Selected result number is unavailable in this enumeration");
    }
  }
  const offline = options2.command === "firmware" && options2.board;
  const makeDevice = dependencies.createDevice ?? createDevice;
  const device = makeDevice(endpoint && !offline ? { transport: (dependencies.transportFor ?? transportFor)(endpoint, options2) } : {});
  let watchObserver;
  let primary;
  let result;
  try {
    if (options2.command === "watch") watchObserver = createWatchObserver(device, options2, dependencies);
    if (endpoint && !offline) {
      emit(dependencies, { event: "state", state: "connecting" });
      await device.connect({
        role: endpoint.interface === "serial" ? "unknown" : endpoint.interface,
        timeout: options2.connectTimeout,
        signal: dependencies.signal,
        probeRepl: shouldProbeRepl(options2),
        ...endpoint.advertisement ? { expectedDevice: endpoint.advertisement } : {}
      });
      emit(dependencies, { event: "state", state: "connected" });
    }
    if (options2.command === "inspect") result = await device.inspect({ fields: options2.fields, timeout: options2.timeout, signal: dependencies.signal });
    else if (options2.command === "configure") {
      const network = {};
      if (options2.ssid) network.credentials = { ssid: options2.ssid, password: await (dependencies.readPassword ?? passwordFromInput)({ ...options2, signal: dependencies.signal }) };
      if (options2["forget-wifi"]) network.credentials = null;
      if (options2["network-enabled"] !== void 0) network.enabled = options2["network-enabled"] === "true";
      await device.configure({ network, timeout: options2.timeout, signal: dependencies.signal });
      result = { ok: true };
    } else if (options2.command === "control") {
      result = await device.control({ action: options2.action, ...options2.mode ? { mode: options2.mode } : {}, timeout: options2.timeout, signal: dependencies.signal });
    } else if (options2.command === "firmware") {
      let catalog = options2.catalog;
      const mode = options2.mode ?? "update";
      if (catalog !== void 0 && !/^https:\/\//.test(catalog)) catalog = JSON.parse(await (dependencies.readFile ?? readFile)(catalog, "utf8"));
      const checked = await device.firmware.check({ catalog, mode, ...endpoint && !offline ? {} : { identity: { board: options2.board, firmwareVersion: options2["current-version"] ?? "unknown" } }, ...options2.version ? { version: options2.version } : {}, signal: dependencies.signal });
      if (options2.subcommand === "check") result = checked;
      else result = await device.firmware.update({ mode, release: checked.release, board: options2.board, ...options2.image ? { data: new Uint8Array(await (dependencies.readFile ?? readFile)(options2.image)) } : {}, openLoader: ({ signal }) => (dependencies.openLoader ?? openNodeRom)({ port: options2.port, python: options2.python, signal }), onPhase: (message) => emit(dependencies, { event: "firmware.phase", message }), signal: dependencies.signal });
    } else if (options2.command === "python") {
      const request = {
        ...options2.source !== void 0 ? { source: options2.source } : {},
        ...options2.file !== void 0 ? { source: await (dependencies.readFile ?? readFile)(options2.file, "utf8") } : {},
        ...options2.path !== void 0 ? { path: options2.path } : {},
        completion: options2.completion,
        maxOutputChars: options2.maxOutputChars,
        ...options2.timeoutExplicit ? { timeout: options2.timeout } : {}
      };
      result = await runPython(device, request, dependencies);
    } else if (options2.command === "files") {
      const signal = dependencies.signal;
      if (options2.subcommand === "list") result = await device.files.list({ path: options2.path, recursive: options2.recursive ?? false, signal });
      else if (options2.subcommand === "read") {
        const data = await device.files.read({ path: options2.path, maxBytes: options2.maxBytes, ...options2.timeoutExplicit ? { timeout: options2.timeout } : {}, signal });
        result = { path: options2.path, ...await writeLocalOutput(options2.output, data, options2.maxBytes, dependencies) };
      } else if (options2.subcommand === "write") {
        const data = await (dependencies.readFile ?? readFile)(options2.file);
        result = await device.files.write({ path: options2.path, data, overwrite: !options2["no-overwrite"], signal });
      } else if (options2.subcommand === "remove") result = await device.files.remove({ path: options2.path, type: options2.type ?? "file", signal });
      else result = await device.files.mkdir({ path: options2.path, recursive: options2.recursive ?? false, signal });
    } else if (options2.command === "capture") {
      const capture = await device.capture({ source: options2.source, format: "jpeg", ...options2.quality ? { quality: options2.quality } : {}, ...options2.timeoutExplicit ? { timeout: options2.timeout } : {}, signal: dependencies.signal });
      const saved = await writeLocalOutput(options2.output, capture.data, options2.maxBytes, dependencies);
      result = { source: options2.source, mimeType: capture.mimeType ?? "image/jpeg", metadata: capture.metadata ?? null, ...saved };
    } else if (options2.command === "batch") result = await runBatch(device, options2, plan, dependencies);
    else if (options2.command === "watch") result = await watchObserver.wait();
  } catch (failure3) {
    primary = failure3;
  }
  if (!primary && options2.command === "watch" && result?.cancelled && dependencies.signal?.aborted) {
    primary = error("CANCELLED", "Watch cancelled", { result });
  }
  watchObserver?.close();
  try {
    await device.disconnect();
  } catch (cleanupFailure) {
    primary = attachCleanupFailure(primary, cleanupFailure);
  }
  emit(dependencies, { event: "state", state: "disconnected" });
  if (primary && endpoint?.interface !== "tcp" && (endpoint || options2.port)) {
    primary = await explainSerialFailure(primary, options2, dependencies);
  }
  const durationMs = Date.now() - startedAt;
  emit(dependencies, { event: "duration", milliseconds: durationMs });
  if (primary) {
    if (primary.batchReport && primary.cleanupError) primary.batchReport.cleanupError = primary.cleanupError;
    if (options2.command === "batch" && !primary.batchReport) {
      const completed = result?.completed ?? [];
      primary.batchReport = {
        schemaVersion,
        ok: false,
        command: "batch",
        completed,
        failed: { index: completed.length + 1, operation: completed.length ? "disconnect" : "connect", error: errorInfo(primary) }
      };
    }
    throw primary;
  }
  if (result && typeof result === "object" && !Array.isArray(result) && result.command === "batch") result.durationMs = durationMs;
  return result;
}
var safe = (value) => String(value ?? "\u2014").replace(/[\x00-\x1f\x7f-\x9f]/g, "?");
var graphemes = new Intl.Segmenter(void 0, { granularity: "grapheme" });
function wrapCell(value, width) {
  const lines = [];
  let line = "", used = 0;
  for (const { segment } of graphemes.segment(value)) {
    const size = stringWidth(segment);
    if (used + size > width && line) {
      lines.push(line);
      line = "";
      used = 0;
    }
    line += segment;
    used += size;
  }
  lines.push(line);
  return lines;
}
function formatResult(result, { columns = process.stdout.columns ?? 120 } = {}) {
  if (!result?.devices) return JSON.stringify(result, null, 2);
  const headers = ["#", "Group", "Interface", "Address", "Status", "Board", "Firmware", "Device ID", "USB serial", "Hostname", "USB VID:PID", "USB product", "Error"];
  const rows = result.devices.map((row) => [row.number, row.group, row.interface, row.address, row.status, row.identity?.board, row.identity?.firmwareVersion, row.identity?.deviceId, row.usb?.serialNumber, row.identity?.hostname, row.usb?.vendorId == null ? null : `${row.usb.vendorId.toString(16).padStart(4, "0")}:${(row.usb.productId ?? 0).toString(16).padStart(4, "0")}`, row.usb?.product, row.error?.code].map(safe));
  if (!rows.length) return "No devices found.";
  const widths = headers.map((header, index) => Math.max(stringWidth(header), ...rows.map((row) => stringWidth(row[index]))));
  if (widths.reduce((sum, width) => sum + width, 0) + 2 * (headers.length - 1) <= columns) {
    return [headers, ...rows].map((row) => row.map((value, index) => value + " ".repeat(widths[index] - stringWidth(value))).join("  ").trimEnd()).join("\n");
  }
  const labelWidth = Math.max(...headers.map((value) => stringWidth(value)));
  const indent = " ".repeat(labelWidth + 2);
  return rows.map((row) => headers.map((header, index) => {
    const lines = wrapCell(row[index], Math.max(2, columns - indent.length));
    return `${header.padEnd(labelWidth)}: ${lines.join(`
${indent}`)}`;
  }).join("\n")).join("\n\n");
}
function successEnvelope(command, result) {
  if (result?.command === "batch" && result.ok === false) return result;
  return { schemaVersion, ok: true, command, result };
}
function failureEnvelope(command, failure3) {
  if (failure3?.batchReport) return failure3.batchReport;
  return {
    schemaVersion,
    ok: false,
    command,
    error: errorInfo(failure3),
    ...failure3?.result ? { result: failure3.result } : {},
    ...failure3?.cleanupError ? { cleanupError: failure3.cleanupError } : {}
  };
}
function formatCliResult(command, result) {
  if (command === "python") {
    if (result?.started) return `Python start acknowledged for ${result.path}. Disconnected after ${result.durationMs} ms.`;
    return `Python completed in ${result?.durationMs ?? 0} ms; observed output was sent to stderr.`;
  }
  if (command === "batch") {
    const visible = structuredClone(result);
    for (const entry of visible.completed ?? []) {
      if (entry.result && typeof entry.result === "object") delete entry.result.output;
    }
    return formatResult(visible);
  }
  return formatResult(result);
}
function mainCommandName(options2) {
  return options2.command === "firmware" || options2.command === "files" ? [options2.command, options2.subcommand].filter(Boolean).join(" ") : options2.command;
}
function commandContext(args) {
  try {
    const { positionals } = parseCommandOptions(args, false);
    return { command: positionals[0] ?? "inspect", subcommand: positionals[1] };
  } catch {
    return { command: args[0] && !args[0].startsWith("-") ? args[0] : "unknown" };
  }
}
function isMain() {
  try {
    return Boolean(process.argv[1]) && pathToFileURL(realpathSync(process.argv[1])).href === import.meta.url;
  } catch {
    return false;
  }
}
if (isMain()) {
  let signalName;
  const jsonRequested = process.argv.includes("--json");
  const controller = new AbortController();
  const abort2 = (name) => {
    signalName = name;
    controller.abort(error("CANCELLED", `Command cancelled by ${name}`));
  };
  const onInterrupt = () => abort2("SIGINT");
  const onTerminate = () => abort2("SIGTERM");
  process.once("SIGINT", onInterrupt);
  process.once("SIGTERM", onTerminate);
  let options2 = commandContext(process.argv.slice(2));
  try {
    options2 = parseCli(process.argv.slice(2));
    const command = options2.help ? "help" : mainCommandName(options2);
    const result = await runCli(options2, {
      signal: controller.signal,
      onEvent: (event) => process.stderr.write(`${JSON.stringify(event)}
`),
      onPhase: (message) => process.stderr.write(`${JSON.stringify({ schemaVersion, event: "firmware.phase", message })}
`)
    });
    if (options2.help) {
      const help = { usage, capabilities: cliCapabilities };
      process.stdout.write(options2.json ? JSON.stringify(successEnvelope("help", help)) + "\n" : usage + "\n");
    } else {
      const envelope = successEnvelope(command, result);
      process.stdout.write(options2.json ? JSON.stringify(envelope) + "\n" : formatCliResult(command, result) + "\n");
      for (const warning of result?.warnings ?? []) process.stderr.write(`${JSON.stringify({ schemaVersion, event: "warning", source: warning.source, message: warning.message })}
`);
    }
  } catch (failure3) {
    const command = options2.help ? "help" : mainCommandName(options2);
    const envelope = failureEnvelope(command, failure3);
    if (failure3.code === "ARGUMENT" || failure3.code === "INVALID_PLAN" || failure3.code?.startsWith("ERR_PARSE_ARGS")) {
      envelope.error ??= errorInfo(failure3);
      process.exitCode = 2;
    } else process.exitCode = signalName === "SIGINT" ? 130 : signalName === "SIGTERM" ? 143 : 1;
    if (options2.json || jsonRequested) process.stdout.write(JSON.stringify(envelope) + "\n");
    else process.stdout.write(`${envelope.error?.message ?? "Command failed"}
`);
    process.stderr.write(`${JSON.stringify({ schemaVersion, event: signalName ? "cancelled" : "error", ...errorInfo(failure3), ...failure3.cleanupError ? { cleanupError: failure3.cleanupError } : {} })}
`);
  } finally {
    process.removeListener("SIGINT", onInterrupt);
    process.removeListener("SIGTERM", onTerminate);
  }
}
export {
  cliCapabilities,
  defaultPython,
  failureEnvelope,
  filterSerialPorts,
  formatResult,
  inventory,
  listSerial,
  parseCli,
  runCli,
  serialEntry,
  successEnvelope,
  transportFor,
  usage
};
