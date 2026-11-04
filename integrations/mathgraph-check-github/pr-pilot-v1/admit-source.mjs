import {isFiniteMethod,finiteGate} from './finite-methods.mjs';
import {REPORT_METHOD,admitReportSources} from './report-integrity.mjs';
import {GENERATOR_METHOD,GENERATOR_GATE} from './traceof-comments.mjs';
import {readFile} from 'node:fs/promises';import {createHash} from 'node:crypto';import {admitPilotSources,validatePilotSnapshot} from './engine.mjs';
const root=process.argv[2],s=JSON.parse(await readFile(root+'/snapshot.json'));
validatePilotSnapshot(s);
if(createHash('sha256').update(s.cli_source).digest('hex')!==(isFiniteMethod(s.method)?createHash('sha256').update(finiteGate(s.method)).digest('hex'):'64bb20331484ef711b6a752af1770959164c82308fd9ae79fbf954678ebbdbcf'))throw Error('CLI_NOT_REVIEWED');
(s.method===REPORT_METHOD?admitReportSources:admitPilotSources)(s.base_source??s.source,s.source);
try{const p=JSON.parse(await readFile(root+'/patch.json'));(s.method===REPORT_METHOD?admitReportSources:admitPilotSources)(s.source,p.content);}catch(e){if(e.code!=='ENOENT')throw e;}
