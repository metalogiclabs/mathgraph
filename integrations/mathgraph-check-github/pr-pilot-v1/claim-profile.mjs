// Trusted, exact-subject capability registration. A different PR may replay the
// same immutable calibration source; it does not become fresh validation.
export function claimProfileFor(r){return r?.repository==='metalogiclabs/L4YAML'&&r.command==='check'&&r.profile?.mode==='OWNED_FORK_CLI_PARITY'&&r.profile.cli_profile==='traceof'&&r.base_sha==='1f97fbf881da6d1b9e2a7b9c547d1d3306f518ff'&&r.head_sha==='1153d648425fb15f6fe49061544f7ffe4bdcb520'?{id:'empty-tail-v1',upstream:'nasa-jpl/L4YAML',upstream_pr:212}:null;}
