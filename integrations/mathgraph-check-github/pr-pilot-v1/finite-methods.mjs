import {GENERATOR_METHOD,GENERATOR_GATE,GENERATOR_PROFILE,admitProfilePatch} from './traceof-comments.mjs';
import {REPORT_METHOD,REPORT_GATE,REPORT_PROFILE,admitReportPatch} from './report-integrity.mjs';
export const isFiniteMethod=m=>[GENERATOR_METHOD,REPORT_METHOD].includes(m);
export const finiteProfile=m=>m===REPORT_METHOD?REPORT_PROFILE:m===GENERATOR_METHOD?GENERATOR_PROFILE:null;
export const finiteGate=m=>m===REPORT_METHOD?REPORT_GATE:m===GENERATOR_METHOD?GENERATOR_GATE:null;
export const admitFinitePatch=(p,source,snapshot)=>snapshot?.method===REPORT_METHOD?admitReportPatch(p,source):admitProfilePatch(p,source,snapshot);
