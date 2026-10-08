from memebot.core.config import Settings
s=Settings()
print({k:str(getattr(s,k)) for k in ['execution_mode','paper_trading_enabled','starting_capital','starting_capital_currency','paper_base_position_percent','paper_max_position_percent','paper_min_order_amount','paper_stop_loss_percent','paper_max_holding_seconds','paper_runner_max_holding_seconds','ollama_model','alpha_filter_enabled','pulse_enabled']})
print({'pumpportal_configured':s.pumpportal_api_key is not None,'telegram_configured':s.telegram_bot_token is not None})
