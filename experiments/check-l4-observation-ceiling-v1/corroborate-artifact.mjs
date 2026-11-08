/**
 * Read-only reproducibility tool for one pinned historical L4YAML proof ZIP.
 * This local policy is reviewable evidence, NOT a protected production trust
 * root. It does not download the artifact or rerun the Lean kernel.
 * Usage: node corroborate-artifact.mjs path/to/whole-source-directive-evidence.zip
 */
import {corroborateLeanProofArtifact} from
 '../../integrations/mathgraph-check-github/proof-artifact-corroboration-v1.mjs';

const path=process.argv[2];
if(!path||process.argv.length!==3){
 process.stderr.write('Usage: node corroborate-artifact.mjs <downloaded-artifact.zip>\n');
 process.exitCode=2;
}else{
 const pinned={
  repository:'metalogiclabs/L4YAML',
  commit:'b882e5b298b30b094f4154da7108a45e196cfcd3',
  run:42420433923,job:128547467405,
  theorem:'MathGraph.WholeSource.CapstoneCommentBoundary.no_normative_iff_on_frozen_runtime',
  artifact_sha256:'f60e48bc7a9df0e618c9ce6398644a9bbc5da4d4022010528f662f0566a536f3',
  lean_build_commit:'eb6cafb7290e8bd5f2937522d8d804f58f02bafc',
  expected_theorem_type:
   'MathGraph.WholeSource.CapstoneCommentBoundary.no_normative_iff_on_frozen_runtime (Language : String → Prop)\n'+
   '  (hchar : ∀ (s : String), Language s → MathGraph.WholeSource.CapstoneCommentBoundary.NoRawSOH s) :\n'+
   '  ¬∀ (s : String), MathGraph.WholeSource.CapstoneObstructions.Accepted s ↔ Language s',
 };
 const result=corroborateLeanProofArtifact(path,pinned);
 process.stdout.write(JSON.stringify(result,null,2)+'\n');
 if(result.status!=='CORROBORATED')process.exitCode=1;
}
