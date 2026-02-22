#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
using System.IO;
#endregion

//This namespace holds Strategies in this folder and is required. Do not change it. 
namespace NinjaTrader.NinjaScript.Strategies
{
	public class ExportAccountStatus : Strategy
	{
		private string path = @"C:\Data\AccountStatus.csv";
        private object fileLock = new object();

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Exports account data for Python consumption.";
				Name										= "ExportAccountStatus";
				Calculate									= Calculate.OnEachTick;
				EntriesPerDirection							= 1;
				EntryHandling								= EntryHandling.AllEntries;
				IsExitOnSessionCloseStrategy				= true;
				ExitOnSessionCloseSeconds					= 30;
				IsFillLimitOnTouch							= false;
				MaximumBarsLookBack							= MaximumBarsLookBack.TwoHundredFiftySix;
				OrderFillResolution							= OrderFillResolution.Standard;
				Slippage									= 0;
				StartBehavior								= StartBehavior.WaitUntilFlat;
				TimeInForce									= TimeInForce.Gtc;
				TraceOrders									= false;
				RealtimeErrorHandling						= RealtimeErrorHandling.StopCancelClose;
				StopTargetHandling							= StopTargetHandling.PerEntryExecution;
				BarsRequiredToTrade							= 20;
				// Disable this property for performance gains in Strategy Analyzer optimizations
				// See the Help Guide for additional information
				IsInstantiatedOnEachOptimizationIteration	= true;
			}
			else if (State == State.Configure)
			{
			}
            else if (State == State.DataLoaded)
            {
               // Ensure directory exists
               string dir = Path.GetDirectoryName(path);
               if (!Directory.Exists(dir))
               {
                   Directory.CreateDirectory(dir);
               }
            }
		}

		protected override void OnBarUpdate()
		{
            // Run only once per minute or on every bar if preferred. 
            // For efficiency, maybe check Time[0] minute change.
            if (BarsInProgress == 0 && IsFirstTickOfBar)
            {
                ExportData();
            }
		}

        private void ExportData()
        {
            try
            {
                lock (fileLock)
                {
                    StringBuilder sb = new StringBuilder();
                    sb.AppendLine("AccountName,Balance,StartBalance,DailyLoss,OpenPnL");

                    foreach (Account acc in Account.All)
                    {
                        // Filter for relevant accounts if needed
                        string name = acc.Name;
                        double balance = acc.Get(AccountItem.CashValue, Currency.UsDollar);
                        double startBalance = acc.Get(AccountItem.InitialMargin, Currency.UsDollar); // Proxy or custom
                         // Note: StartBalance might need manual tracking or different API call depending on broker
                        if (startBalance == 0) startBalance = 100000; // Default fallback

                        double dailyLoss = 0; // NinjaTrader doesn't expose "Daily Loss" directly easily without tracking.
                        // We might use RealizedProfitLoss + Unrealized
                        double realized = acc.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
                        double unrealized = acc.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar);
                        dailyLoss = realized + unrealized; // Approx daily PnL reset

                        sb.AppendLine(string.Format("{0},{1},{2},{3},{4}", 
                            name, balance, startBalance, dailyLoss, unrealized));
                    }

                    File.WriteAllText(path, sb.ToString());
                }
            }
            catch (Exception ex) 
            {
                Print("Export failed: " + ex.Message);
            }
        }
	}
}
