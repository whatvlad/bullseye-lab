from pathlib import Path
p=Path('src/memebot/paper/candidate_proof.py');s=p.read_text()
s=s.replace('        self._order_transactions(proof, transactions)\n','''        # Same-slot multiple transactions lack a trustworthy index in signature RPC.
        if len({row[0] for row in transactions}) != len(transactions):
            raise ProofFailure("FAIL_STATE_SYNC", "same-slot transaction order unproven")
        transactions.sort(key=lambda row: row[0])
''')
s=s.replace('        bundle = await self._terminal_bank(proof, previous, bundle, transactions, parities)\n','''        if previous != {key: bundle["curve"][key] for key in previous or {}}:
            raise ProofFailure(
                "FAIL_STATE_SYNC", "terminal transaction state differs from atomic snapshot"
            )
''')
a=s.index('            proof.evidence["history_fence_changes"]');b=s.index('            raise ProofFailure("FAIL_STATE_SYNC", "history fence moved during proof")',a);s=s[:a]+s[b:]
a=s.index('    def _order_transactions(');b=s.index('    async def execution_refresh(',a);s=s[:a]+s[b:];p.write_text(s)
