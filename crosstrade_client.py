import requests
import logging

class CrossTradeClient:
    def __init__(self, api_key, hook_url="N/A"):
        self.api_key = api_key
        # Your specific Webhook URL
        self.webhook_url = "https://app.crosstrade.io/v1/send/Hunm2Ve4/1PG9b8GEukklVI8pnmeT3Q"
        
        self.logger = logging.getLogger("CrossTradeClient")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def send_signal(self, symbol, action, quantity, order_type="MARKET", strategy=None, **kwargs):
        """
        Sends a signal mimicking a TradingView Alert.
        PRECISION MODE: Sends EXACTLY what the CrossTrade Manual Trader expects.
        """
        # [FIX] Use the command passed from Commander (or default to PLACE)
        cmd = kwargs.get('command', 'PLACE')

        # --- PAYLOAD CONSTRUCTION ---
        if cmd == "CLOSEPOSITION":
            # [CRITICAL FIX] Match the Manual Trader screenshot EXACTLY.
            # NO strategy, NO tif, NO action. Just the 4 essentials.
            payload_str = (
                f"key={self.api_key};"
                f"command=CLOSEPOSITION;"
                f"account=Sim101;"
                f"instrument={symbol};"
            )
        else:
            # FOR REGULAR TRADES (PLACE), SEND FULL DATA
            payload_str = (
                f"key={self.api_key};"
                f"command={cmd};"
                f"account=Sim101;"
                f"instrument={symbol};"
                f"action={action};"
                f"qty={quantity};"
                f"order_type={order_type};"
                f"tif=DAY;"
            )
            # Only add strategy for PLACE commands
            if strategy and strategy != "None":
                payload_str += f"strategy={strategy};"
            
            # Add Dynamic Params (Stop Loss / Take Profit) - ONLY for PLACE commands
            for key, value in kwargs.items():
                if key == 'command': continue 
                
                if key == "stop_loss":
                    if action.upper() == "BUY":
                        payload_str += f"stop_loss=-{value} ticks;"
                    else:
                        payload_str += f"stop_loss={value} ticks;"
                        
                elif key == "take_profit":
                    if action.upper() == "BUY":
                        payload_str += f"take_profit={value} ticks;"
                    else:
                        payload_str += f"take_profit=-{value} ticks;"
                else:
                    payload_str += f"{key}={value};"

        try:
            self.logger.info(f"🚀 Sending Signal: {payload_str}")
            
            headers = {
                'Content-Type': 'text/plain',
                'User-Agent': 'TradingView_Alert/1.0'
            }
            
            response = requests.post(self.webhook_url, data=payload_str, headers=headers)
            
            if response.status_code == 200:
                self.logger.info(f"✅ CrossTrade Server Response: {response.text}")
                return True
            else:
                self.logger.error(f"❌ CrossTrade Rejected ({response.status_code}): {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Connection Failed: {e}")
            return False