import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

def determine_bin_size(price):
    if price < 20:
        return 0.5
    elif price < 100:
        return 1
    elif price < 200:
        return 2
    elif price < 500:
        return 5
    else:
        return 10

def plot_options_data(frame, options_df, global_max_pain, local_max_pain, price, ticker, expiration, combined_view=False):
    bin_size = determine_bin_size(price)

    strikes = options_df['strike']

    min_strike = strikes.min()
    max_strike = strikes.max()
    bins = np.arange(min_strike - bin_size, max_strike + 2 * bin_size, bin_size)

    # Clear previous widgets
    for widget in frame.winfo_children():
        widget.destroy()

    fig = plt.Figure(figsize=(7.5, 4.5), dpi=100)
    ax = fig.add_subplot(111)

    width = bin_size * 0.4

    if combined_view:
        # Group calls and puts separately
        calls_df = options_df[options_df['type'] == 'call'].copy()
        puts_df = options_df[options_df['type'] == 'put'].copy()

        calls_df['strike_bin'] = pd.cut(calls_df['strike'], bins=bins, include_lowest=True, right=False)
        puts_df['strike_bin'] = pd.cut(puts_df['strike'], bins=bins, include_lowest=True, right=False)

        calls_grouped = calls_df.groupby('strike_bin').agg({'volume':'sum', 'openInterest':'sum'}).reset_index()
        puts_grouped = puts_df.groupby('strike_bin').agg({'volume':'sum', 'openInterest':'sum'}).reset_index()

        # Calculate bin centers
        calls_grouped['bin_center'] = calls_grouped['strike_bin'].apply(lambda x: x.left + bin_size/2).astype(float)
        puts_grouped['bin_center'] = puts_grouped['strike_bin'].apply(lambda x: x.left + bin_size/2).astype(float)

        # Plot calls and puts volume side by side
        ax.bar(calls_grouped['bin_center'] - width/2, calls_grouped['volume'], width=width, label='Calls Volume', color='blue', alpha=0.7)
        ax.bar(puts_grouped['bin_center'] + width/2, puts_grouped['volume'], width=width, label='Puts Volume', color='red', alpha=0.7)

        # Optionally, if you want to also plot open interest as lighter bars stacked or with different hatch, you could add that here.

        # Set x-ticks from combined strike bins (union)
        all_bin_centers = sorted(set(calls_grouped['bin_center']).union(set(puts_grouped['bin_center'])))
        ax.set_xticks(all_bin_centers)
        ax.set_xticklabels([f"{x:.2f}" for x in all_bin_centers], rotation=45)

    else:
        # Existing single-type plotting (calls or puts or all combined)
        options_df['strike_bin'] = pd.cut(options_df['strike'], bins=bins, include_lowest=True, right=False)
        grouped = options_df.groupby('strike_bin').agg({'volume':'sum', 'openInterest':'sum'}).reset_index()
        grouped['bin_center'] = grouped['strike_bin'].apply(lambda x: x.left + bin_size/2).astype(float)

        ax.bar(grouped['bin_center'] - width/2, grouped['volume'], width=width, label='Volume', alpha=0.7)
        ax.bar(grouped['bin_center'] + width/2, grouped['openInterest'], width=width, label='Open Interest', alpha=0.7)

        ax.set_xticks(grouped['bin_center'])
        ax.set_xticklabels([f"{x:.2f}" for x in grouped['bin_center']], rotation=45)

    # Draw vertical lines for max pains and current price
    def get_bin_center_for_strike(strike):
        for b in bins[:-1]:
            if b <= strike < b + bin_size:
                return b + bin_size / 2
        return None

    global_x = get_bin_center_for_strike(global_max_pain)
    local_x = get_bin_center_for_strike(local_max_pain) if local_max_pain is not None else None

    if global_x:
        ax.axvline(x=global_x, color='orange', linestyle='--', linewidth=2, label='Global Max Pain')
    if local_x and local_x != global_x:
        ax.axvline(x=local_x, color='teal', linestyle='--', linewidth=2, label='Local Max Pain')

    ax.axvline(x=price, color='green', linestyle='--', linewidth=2, label='Current Price')

    ax.set_title(f"{ticker} Options Expiring {expiration} (Bin Size: ${bin_size})")
    ax.set_xlabel("Strike Price")
    ax.set_ylabel("Contracts")
    ax.legend()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

    toolbar = NavigationToolbar2Tk(canvas, frame)
    toolbar.update()
    toolbar.pack(fill='x')

    original_xlim = ax.get_xlim()
    original_ylim = ax.get_ylim()

    return fig, options_df, original_xlim, original_ylim, canvas, ax
