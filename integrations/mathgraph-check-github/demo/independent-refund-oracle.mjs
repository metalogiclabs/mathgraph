// SYNTHETIC customer-authored intent oracle, independent of the agent function.
export function expectedRefund(order) {
  if (!order || !Number.isFinite(order.amount) || order.amount < 0)
    return {status:'DENIED_INVALID_INPUT',amount:0};
  if (order.status==='REFUNDED')
    return {status:'DENIED_ALREADY_REFUNDED',amount:0};
  return {status:'REFUNDED',amount:order.amount};
}
