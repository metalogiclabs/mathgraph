// Repository capability allowlist, independent of bugs, theorem names or repairs.
export function subjectPolicy(env={}){
 const source=env.MATHGRAPH_SOURCE_REPOSITORY??'Stanford-NavLab/gnss_lib_py';
 if(!['Stanford-NavLab/gnss_lib_py','metalogiclabs/gnss_lib_py'].includes(source))throw Error('UNREVIEWED_REPOSITORY_PROFILE');
 const raw=env.MATHGRAPH_PR_NUMBER;
 if(raw!==undefined&&(!/^[1-9][0-9]*$/.test(raw)||!Number.isSafeInteger(Number(raw))))throw Error('INVALID_PR_SELECTOR');
 return {repository:'metalogiclabs/gnss_lib_py',source_repository:source,implementation_prefix:'gnss_lib_py/',max_prs:10,...(raw?{requested_pr:Number(raw)}:{})};
}
