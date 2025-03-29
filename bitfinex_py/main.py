from bfxapi import Client
import time
import datetime
from threading import Thread

class AutoLendingBitfinex:
    def __init__(self, api_key, api_secret):
        self.client = Client(api_key=api_key, api_secret=api_secret)
        self.lowest_price = 0.00025
        self.set_aside_funds = 0
        self.unit_amount = 150
        self.runner_pass = False
        self.init = False

    def main(self):
        print("放貸機器人 ver 1.00")
        while True:
            if not self.init:
                self.task = Thread(target=self.main_runner)
                self.task.start()
                self.init = True
            enter_common = input()
            self.read_common(enter_common)

    def main_runner(self):
        while self.runner_pass:
            time.sleep(1)
        print("運轉中...")
        # 獲取資產餘額
        balances = self.client.rest.auth.get_wallets()
        usd_remaining = next((x['balanceAvailable'] for x in balances if x['type'] == 'funding' and x['currency'] == 'USD'), 0)
        usd_remaining -= self.set_aside_funds  # 扣掉使用者想要預留的資金

        # 如果USD剩餘有超過150
        if usd_remaining >= self.unit_amount:
            if self.get_active_funding_offers_count() == 0:
                # 借出金額
                quantity = self.unit_amount if usd_remaining - self.unit_amount >= self.unit_amount else round(usd_remaining, 3) - 0.001
                # 限定利率
                rate = self.get_avg()
                # 設定日期
                period = self.set_period(rate)
                if rate != 0:
                    submit_funding_offer = self.client.rest.auth.submit_offer('fUSD', quantity, rate, period)
                    if 'id' in submit_funding_offer:
                        print(f"已送出融資訂單 , Rate {rate} day {period}")
                    else:
                        print("送出融資訂單錯誤!")
                        print(f"SubmitFundingOffer Error {submit_funding_offer.get('message', '')}")
        else:
            self.get_active_funding_offers_count()

        self.delay_main_runner()

    def delay_main_runner(self):
        time.sleep(10)
        self.main_runner()

    def get_active_funding_offers_count(self):
        active_funding_offers = self.client.rest.auth.get_active_offers('fUSD')
        if active_funding_offers:
            if len(active_funding_offers) > 0 and round(self.get_avg(), 6) != round(float(active_funding_offers[0]['rate']), 6):
                print(f"已有訂單 利率: {active_funding_offers[0]['rate']} 天數: {active_funding_offers[0]['period']}")
                self.client.rest.auth.cancel_offer(active_funding_offers[0]['id'])
                print("更新訂單")
            return len(active_funding_offers)
        else:
            print(f"獲取訂單錯誤 {active_funding_offers.get('message', '')}")
            return -1

    def get_avg(self):
        kline_data = self.client.rest.public.get_candles('fUSD', '30m', start=datetime.datetime.utcnow() - datetime.timedelta(hours=12))
        if kline_data:
            high_price = sorted([x['high'] for x in kline_data], reverse=True)[:11]
            avg = sum(high_price) / len(high_price)
            print(avg)
            # 檢查最新價格是不是比avg還高
            trade_history = self.client.rest.public.get_trades('fUSD', start=datetime.datetime.utcnow() - datetime.timedelta(minutes=30))
            if trade_history:
                if trade_history[0]['price'] > avg:
                    avg = trade_history[0]['price']
                    print(f"Avg被市場價格刷新 {avg}")
            else:
                print(f"Trade history error {trade_history.get('message', '')}")
                return 0
            print(f"AVG {avg}")
            return avg if avg > self.lowest_price else self.lowest_price
        else:
            return 0

    def set_period(self, rate):
        if rate < 0.0003:
            return 2
        if rate < 0.0004:
            return 7
        return 30

    def read_common(self, common):
        commands = {
            "Clear": self.clear,
            "SetLowestPrice": self.set_lowest_price,
            "SetAsideFunds": self.set_aside_funds,
            "SetUnitAmount": self.set_unit_amount
        }
        if common in commands:
            commands[common]()
        else:
            print("指令錯誤!")

    def clear(self):
        print("\033c", end="")

    def set_lowest_price(self):
        self.runner_pass = True
        print("請輸入要設定的最低利率\n利率換算方式 0.00025 = 0.025% (請以 *0.00025* 這個格式來設定)\n請注意不要超過7% Bitfinex不允許 ")
        set_lowest_rate = input()
        try:
            result = float(set_lowest_rate)
            if result > 0.07 or result <= 0:
                print("更新失敗\n請注意不要超過7%的限制!")
            else:
                self.lowest_price = result
                print("已更新最低利率")
        except ValueError:
            print("設定失敗")
        self.runner_pass = False

    def set_aside_funds(self):
        self.runner_pass = True
        print("請輸入想要預留的資金\n*這邊只能輸入整數*")
        set_aside_funds = input()
        try:
            result = int(set_aside_funds)
            if result < 0:
                self.set_aside_funds = 0
                print("已將預留資金設定為 0")
            else:
                self.set_aside_funds = result
                print(f"已將預留資金設定為 {result}")
        except ValueError:
            print("設定失敗")
        self.runner_pass = False

    def set_unit_amount(self):
        self.runner_pass = True
        print("請輸入一單的最低金額\n*這邊只能輸入整數*")
        set_unit_amount = input()
        try:
            result = int(set_unit_amount)
            if result < 150:
                self.unit_amount = 150
                print("已將最低金額設定為 150")
            else:
                self.unit_amount = result
                print(f"已將最低金額設定為 {result}")
        except ValueError:
            print("設定失敗")
        self.runner_pass = False

if __name__ == "__main__":
    api_key = input("請輸入API 金鑰 : ")
    api_secret = input("請輸入API 密鑰 : ")
    bot = AutoLendingBitfinex(api_key, api_secret)
    bot.main()