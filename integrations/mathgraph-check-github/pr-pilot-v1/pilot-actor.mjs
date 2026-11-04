const ensure=(b,c)=>{if(!b)throw Error(c);};
export async function readPilotActor(item,api,pilotOperators=[]){
 ensure(item.repository==='metalogiclabs/L4YAML'&&Number.isSafeInteger(item.number)&&item.number>0&&Number.isSafeInteger(item.comment_id)&&item.comment_id>0,'ACTOR_ORIGIN_INVALID');
 const root='/repos/'+item.repository,pr=await api(root+'/pulls/'+item.number),comment=await api(root+'/issues/comments/'+item.comment_id);
 ensure(pr.state==='open'&&['head','base'].every(s=>pr[s]?.repo?.full_name===item.repository&&pr[s].repo.private===false),'ACTOR_ORIGIN_INVALID');
 ensure(comment.id===item.comment_id&&comment.issue_url==='https://api.github.com'+root+'/issues/'+item.number&&comment.user?.type==='User'&&Number.isSafeInteger(comment.user.id)&&comment.user.id>0&&/^[A-Za-z0-9-]{1,39}$/.test(comment.user.login??''),'ACTOR_COMMENT_INVALID');
 const permission=(await api(root+'/collaborators/'+comment.user.login+'/permission')).permission,maintainer=['admin','maintain','write'].includes(permission),allowed=maintainer||pilotOperators.includes(comment.user.id);
 return {pr,comment,permission,allowed,actor_id:comment.user.id,actor_login:comment.user.login,actor_authorization:maintainer?'REPOSITORY_MAINTAINER':'PILOT_OPERATOR'};
}
