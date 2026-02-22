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
	public class TradeLogger : Strategy
	{
        private string path = @"C:\Data\TradeLog.csv";
        
		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Logs trades to CSV.";
				Name										= "TradeLogger";
				Calculate									= Calculate.OnBarClose;
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
				IsInstantiatedOnEachOptimizationIteration	= true;
			}
            else if (State == State.DataLoaded)
            {
                // Init header if not exists
                 string dir = Path.GetDirectoryName(path);
                   if (!Directory.Exists(dir))
                   {
                       Directory.CreateDirectory(dir);
                   }
                if (!File.Exists(path))
                {
                    File.WriteAllText(path, "Time,Symbol,Action,Quantity,Price,Profit\n");
                }
            }
		}

		protected override void OnBarUpdate()
		{
			// Logic is event driven via OnExecutionUpdate ideally
		}
        
        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            // Log every execution
            try
            {
               string action = marketPosition == MarketPosition.Long ? "BUY" : "SELL";
               // Note: This is simplified. Execution update comes for entry and exit.
               // We might want to filter or log all.
               
               // Append to file
               string line = string.Format("{0},{1},{2},{3},{4},0", time, execution.Instrument.FullName, action, quantity, price);
               File.AppendAllText(path, line + Environment.NewLine);
            }
            catch (Exception ex)
            {
                Print("Log failed: " + ex.Message);
            }
        }
	}
}
