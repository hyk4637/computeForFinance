# -*- coding: utf-8 -*-
"""
Created on Thu Jun 20 10:15:48 2019

@author: hongsong chou
"""

import threading
import os
from collections import defaultdict, deque
from SingleStock_SingleStockFuturesArbitrageStrategy import SingleStock_SingleStockFuturesArbitrageStrategy


class TradingPlatform:

    ssfArbStrat = None
    
    def __init__(self, marketData_2_platform_q, platform_2_exchSim_order_q, exchSim_2_platform_execution_q):
        print("[%d]<<<<< call Platform.init" % (os.getpid(),))
        
        # Instantiate individual strategies
        self.ssfArbStrat = SingleStock_SingleStockFuturesArbitrageStrategy(
            "tf_1", "singleStock_singleStockFuturesArbStrategy", "hongsongchou", "2330", "20190706")

        self.future_data_queue = deque(maxlen=2)
        self.execution_map = defaultdict(deque)

        t_md = threading.Thread(name='platform.on_marketData', target=self.consume_marketData,
                                args=(platform_2_exchSim_order_q, marketData_2_platform_q,))
        t_md.start()
        
        t_exec = threading.Thread(name='platform.on_exec', target=self.handle_execution,
                                  args=(exchSim_2_platform_execution_q, ))
        t_exec.start()

    def consume_marketData(self, platform_2_exchSim_order_q, marketData_2_platform_q):
        print('[%d]Platform.consume_marketData' % (os.getpid(),))
        while True:
            book_snap = marketData_2_platform_q.get()
            print('[%d] Platform.on_md' % (os.getpid()))
            print(book_snap.outputAsDataFrame())
            if book_snap.ticker == 'future':
                self.future_data_queue.append(book_snap)
            # result = self.ssfArbStrat.run(book_snap, None)
            elif (book_snap.ticker == 'stock') and (len(self.future_data_queue) != 0):

                future_book_snap = self.future_data_queue.pop()
                paired_book_snapshot = {
                    'stock': book_snap,
                    'future': future_book_snap
                }
                orders_list = self.ssfArbStrat.on_marketData(paired_book_snapshot)
                if orders_list is not None:
                    # do something with the new order
                    if not isinstance(orders_list, list):
                        raise Exception("passed orders should be list")
                    for order in orders_list:
                        platform_2_exchSim_order_q.put(order)
    
    def handle_execution(self, exchSim_2_platform_execution_q):
        print('[%d]Platform.handle_execution' % (os.getpid(),))
        while True:
            execution = exchSim_2_platform_execution_q.get()
            if execution is not None:
                print('[%d] Platform.handle_execution' % (os.getpid()))
                print(execution.outputAsArray())
                self.execution_map[execution.ticker].append(execution)
                if (len(self.execution_map['stock']) >= 1) and (len(self.execution_map['future']) >= 1):
                    paired_execution = {k: l.popleft() for k, l in self.execution_map.items()}
                    self.ssfArbStrat.on_execution(paired_execution)
                # self.ssfArbStrat.run(None, execution)
