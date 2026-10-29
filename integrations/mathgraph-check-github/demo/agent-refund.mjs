// SYNTHETIC AI-agent output. Its happy-path tests are green; behavior is wrong.
export function refund(order) {
  if (!order || !Number.isFinite(order.amount) || order.amount < 0)
    return {status:'DENIED_INVALID_INPUT',amount:0};
  // Bug: no check for an already-refunded order.
  return {status:'REFUNDED',amount:order.amount};
}
