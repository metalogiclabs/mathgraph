// Public review context has no native, specification, or repair authority.
const bot=u=>u?.id===158243242&&u.login==='devin-ai-integration[bot]'&&u.type==='Bot';
const same=(a,b)=>['repository','number','base_sha','head_sha'].every(k=>a?.[k]===b?.[k]);
const limits={review_time_base:'UNKNOWN',private_output:'UNKNOWN',review_settings:'UNKNOWN',equal_information:'UNKNOWN',confirmed_misses:'UNKNOWN',repair_authority:false};
export function publicReviewSummary(packet,subject){
 const unknown=reason=>({status:'UNKNOWN',verdict:'UNKNOWN',reason,...limits});
 if(packet?.complete!==true||!same(packet.subject,subject)||packet.upstream?.repository!=='nasa-jpl/L4YAML'||!Number.isSafeInteger(packet.upstream.number)||packet.upstream.number<1||packet.upstream.base_sha!==subject.base_sha||packet.upstream.head_sha!==subject.head_sha||!Array.isArray(packet.reviews)||!Array.isArray(packet.comments))return unknown('PUBLIC_REVIEW_SOURCE_OR_CAPTURE_INCOMPLETE');
 const all=packet.reviews.filter(r=>bot(r.user)&&Number.isSafeInteger(r.id)&&['COMMENTED','APPROVED','CHANGES_REQUESTED'].includes(r.state)&&!Number.isNaN(Date.parse(r.submitted_at)));
 const exact=all.filter(r=>r.commit_id===subject.head_sha),ids=new Set(exact.map(r=>r.id));
 const comments=packet.comments.filter(c=>bot(c.user)&&ids.has(c.pull_request_review_id)&&c.commit_id===subject.head_sha&&typeof c.body==='string'&&c.body.trim());
 const substantive=exact.filter(r=>typeof r.body==='string'&&r.body.trim());
 const clean=r=>/^## ✅ Devin Review: No Issues Found(?:\r?\n|$)/.test(r.body);
 const verdict=comments.length?'PUBLIC_COMMENTS_PRESENT':substantive.length&&substantive.every(clean)?'NO_ISSUES_REPORTED':substantive.length?'PUBLIC_REVIEW_SUMMARY_PRESENT':'UNKNOWN';
 return {status:'PUBLIC_RECORD_OBSERVED',verdict,...limits,upstream:packet.upstream,review_ids:exact.map(r=>r.id),review_urls:exact.map(r=>`https://github.com/nasa-jpl/L4YAML/pull/${packet.upstream.number}#pullrequestreview-${r.id}`),public_inline_count:comments.length,other_head_inline_count:packet.comments.filter(c=>bot(c.user)&&c.commit_id!==subject.head_sha).length,other_head_review_count:all.length-exact.length,interpretation:'Public record at the same head only. Native evidence retains its own boundary; behavior differences are not automatically defects or reviewer misses.'};
}
export async function capturePublicReview(subject,upstreamNumber,api){
 if(subject.repository!=='metalogiclabs/L4YAML'||!Number.isSafeInteger(upstreamNumber)||upstreamNumber<1)throw Error('PUBLIC_REVIEW_SUBJECT_UNSUPPORTED');
 const root=`/repos/nasa-jpl/L4YAML/pulls/${upstreamNumber}`,pr=await api(root);
 const pageAll=async suffix=>{const items=[];for(let page=1;page<=10;page++){const batch=await api(`${root}/${suffix}?per_page=100&page=${page}`);if(!Array.isArray(batch))throw Error('PUBLIC_REVIEW_CAPTURE_INCOMPLETE');items.push(...batch);if(batch.length<100)return items;}throw Error('PUBLIC_REVIEW_PAGINATION_INCOMPLETE');};
 const [reviews,comments]=await Promise.all([pageAll('reviews'),pageAll('comments')]);
 return {schema:'mathgraph.public-review.capture.v1',captured_at:new Date().toISOString(),subject,upstream:{repository:'nasa-jpl/L4YAML',number:upstreamNumber,base_sha:pr.base?.sha,head_sha:pr.head?.sha},reviews,comments,complete:true};
}
