import {GENERATOR_METHOD,GENERATOR_GATE} from './traceof-comments.mjs';
import {readFile} from 'node:fs/promises';import {createHash} from 'node:crypto';import {admitPilotSources,validatePilotSnapshot} from './engine.mjs';
const root=process.argv[2],s=JSON.parse(await readFile(root+'/snapshot.json'));
validatePilotSnapshot(s);
if(createHash('sha256').update(s.cli_source).digest('hex')!==(s.method===GENERATOR_METHOD?createHash('sha256').update(GENERATOR_GATE).digest('hex'):'64bb20331484ef711b6a752af1770959164c82308fd9ae79fbf954678ebbdbcf'))throw Error('CLI_NOT_REVIEWED');
admitPilotSources(s.base_source??s.source,s.source);
try{const p=JSON.parse(await readFile(root+'/patch.json'));admitPilotSources(s.source,p.content);}catch(e){if(e.code!=='ENOENT')throw e;}
