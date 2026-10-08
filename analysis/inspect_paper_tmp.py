import sys
sys.path.insert(0,'tests')
from test_adaptive_sizing import simulate
_,(amount,result)=simulate(liquidity_sol=20)
print(amount,result.rejection_reason)
