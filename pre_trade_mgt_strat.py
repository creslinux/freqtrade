# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame


from datetime import datetime


# --------------------------------
class LRSI(IStrategy):
    """
    author@: Creslin

    """
    minimal_roi = {
        "0": 0.20
    }
    # Optimal stoploss designed for the strategy
    stoploss = -0.01

    # Optimal ticker interval for the strategy
    ticker_interval = '2h'

    def get_ticker_indicator(self):
        return int(self.ticker_interval[:-1])

    # def populate_indicators(self, dataframe: DataFrame) -> DataFrame:
    # #RSI
    # dataframe['rsi'] = ta.RSI(dataframe, timeperiod=7)
    #
    #     return dataframe

    # # If using Berlins expose pairs to strategy
    def advise_indicators(self, dataframe: DataFrame, pair: str) -> DataFrame:

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=7)

        return dataframe

    #####
    #  EXAMPLE Strat - buys every even minute sells every odd
    ####
    def populate_buy_trend(self, dataframe: DataFrame) -> DataFrame:
        if int(datetime.now().strftime('%M')) % 2 == 0:
            b=9999
            #print("b is: ", b)
        else:
            b=-9999
        dataframe.loc[
            (
                # L-RSI When below 0.01 / vfi -26
                #(dataframe['lrsi'] < 0.5) &
                #(dataframe['vfi'] <  -4)
                (dataframe['vfi'] < b )
            ),
            'buy'] = 1
        return dataframe

    #####
    #  EXAMPLE Strat - buys every even minute sells every odd
    ####
    def populate_sell_trend(self, dataframe: DataFrame) -> DataFrame:
        if int(datetime.now().strftime('%M'))% 2  != 0:
            s=9999
            #print("s is: ", s)
        else:
            s=-9999
        dataframe.loc[
            (
                # vfi 0.99
                #(dataframe['vfi'] > 0.41)
                (dataframe['vfi'] < s )
            ),
            'sell'] = 1
        return dataframe

    def pre_trade_mgt(self, dataframe: DataFrame, pair: str) -> DataFrame:
        """
        pre_trade_mgt. To allow money mamagement and or other checks to be put
        against dataframe with buy/sell.
        """
        """
        Called before a trade executes if exists, backwards compatible.
        pre_trade_mgt to only be called for rows where buy|sell = 1
        and therefore should be very light in terms of overhead

        pre_trade_mgt def is called after:
        > populate_indicators
        > > populate_buy_trend
        > > populate_sell_trend
        > > > pre_trade_mgt  < < <

        The purpose of this def is to allow sanitizing a trade attributes
        and final authorisation prior to being made and after buy or sell are
        set to 1. Allowing greater flexibility and control to a user including
        money management and risk/reward

        Money management and win ratio are key to successful trading.

        It is intended pre_trade will be exposed to data sets including
        - read access(a copy of): trades table, pair, account balance, total capital, orderbook
        - write access: stop-loss, stake, buy and sell index
        - other: a user may write their own logic, calls, tests

            * On backtest a trades table may be created after populate_buy|sell_trend
            are completed. This aligns how back/dry/live can manage pre_trade_mgt processing.

        Examples of feature capacity include.
        1. Cancelling a trade before placed
        2. Altering a stop-loss for a trade
        3. Altering the stake amount for a trade
        4. Sizing stake and stop (basic money management)

        Examples of use-cases include:

        1 query of trades table shows for this pair an unacceptable win/lose ratio.
            - Set buy to 0, or set stake to bare minimum
        2 user only willing to risk 5% of our total capital on a trade
            - size stake and stoploss to ensure this
        3 populate_indicators has added an index to the dataframe hinting to a suitable stop-loss.
            The pair may be known for volatility, or the indicator is proven wrong on a small dip.
            - Set stop-loss to suitable size
        4 the pair has a large/low market cap and is highly/none liquid.
            - increase/reduce stake amount
        5 orderbook shows a large buy wall 1.23% under spot.
            - set stop-loss ontop of this, to mitigate risk its a spoof
        6 any other reason, e.g user does not want to trade on chinese holidays
           - any-hook-they-want: set buy 0


        :param dataframe:
        :param pair:
        :return:
        """

        from freqtrade.persistence import Trade
        import pandas as pd
        df = dataframe

        from pandas import set_option
        set_option('display.max_rows', 2000)
        set_option('display.max_columns', 8)

        def closed_pair_trades(pair):
            """
            To return list of closed trades for a pair
            enriched with open/closd dates, profit, and stake

            :param pair:
            :return: df_c pair open, close, profit, stake
            """
            pair = pair
            df_c = pd.DataFrame(columns=['pair', 'profit', 'open_date', 'close_date', 'stake'])

            pair_trades = Trade.query.filter(Trade.pair.is_(pair)).all()
            for pair_trade in pair_trades:
                if pair_trade.is_open == False:
                    # print("closed trade for", pair, "closed with ", pair_trade.close_profit )

                    p = pair
                    pcp = pair_trade.close_profit
                    od = pair_trade.open_date
                    cd = pair_trade.close_date
                    sa = pair_trade.stake_amount

                    df_c = df_c.append([{'pair':p, 'profit':pcp, 'open_date':od,
                                         'close_date':cd, 'stake':sa}], ignore_index=True)
            return df_c

        def has_past_perf(df_c, lost_the_last=1, out_of=1):
            """
            Return if pair lost_the_last X trades out_of Y trades
            :param df_c: dataframe of closed trades for the pair
            :param lost_the_last: number of bad trades to look for
            :param out_of: within the last number over trades closed
            :return: bool
            """
            lost_the_last =lost_the_last
            out_of = out_of
            df_c = df_c

            df_c_tail = df_c.tail(out_of)
            lost_from_last_count = df_c_tail[df_c_tail['profit'] < 0].shape

            if lost_from_last_count[0] >= lost_the_last:
                return True
            else:
                return False

        # load this pairs closed trades into a df
        df_c = closed_pair_trades(pair=pair)

        # Get bool if on pairs past profitable trades count, cancel the buy if limit hit
        past_perf = has_past_perf(df_c, lost_the_last=9, out_of=10)
        if past_perf:
            #set buy to 0
            df.loc['buy'] = 0

        dataframe  = df
        return dataframe
