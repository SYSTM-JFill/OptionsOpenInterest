import tkinter as tk
from tkinter import ttk, messagebox
import os
from datetime import datetime
from data_fetcher import (
    get_stock_price,
    fetch_options_latest_friday,
    find_max_pain,
    calculate_atr
)
from visualizer import plot_options_data

last_fig = None
last_options_df = None
original_xlim = None
original_ylim = None
canvas = None
ax = None
slider = None

# Globals to store current data for filtering/plotting
current_options_df = None
current_price = None
current_global_max_pain = None
current_local_max_pain = None
current_ticker = None
current_expiration = None

def plot_filtered_data():
    global last_fig, last_options_df, original_xlim, original_ylim, canvas, ax, slider
    if current_options_df is None:
        return
    
    selected_filter = filter_var.get()
    if selected_filter == "Calls":
        filtered_df = current_options_df[current_options_df['type'] == 'call']
        combined_view = False
    elif selected_filter == "Puts":
        filtered_df = current_options_df[current_options_df['type'] == 'put']
        combined_view = False
    else:  # All: combined calls and puts colored separately
        filtered_df = current_options_df
        combined_view = True

    global_max_pain, local_max_pain = find_max_pain(filtered_df, current_price=current_price)

    last_fig, last_options_df, original_xlim, original_ylim, canvas, ax = plot_options_data(
        frame_plot, filtered_df, global_max_pain, local_max_pain, current_price, current_ticker, current_expiration,
        combined_view=combined_view
    )

    update_slider_position(current_price)


def run_analysis():
    global current_options_df, current_price, current_global_max_pain, current_local_max_pain, current_ticker, current_expiration

    ticker = entry_ticker.get().upper()
    if not ticker:
        messagebox.showerror("Error", "Please enter a stock ticker.")
        return

    price = get_stock_price(ticker)
    if price is None:
        messagebox.showerror("Error", f"Could not retrieve price for '{ticker}'.")
        return

    lbl_price.config(text=f"Current Price: ${price:.2f}")

    options_df, expiration = fetch_options_latest_friday(ticker)
    if options_df is None or options_df.empty:
        messagebox.showerror("Error", f"No options data found for '{ticker}'.")
        return

    lbl_expiry.config(text=f"Using Expiration: {expiration}")

    global_max_pain, local_max_pain = find_max_pain(options_df, current_price=price)

    diff = global_max_pain - price
    diff_pct = (diff / price) * 100 if price != 0 else 0

    if local_max_pain is not None:
        lbl_max_pain.config(
            text=(f"Global Max Pain: ${global_max_pain:.2f} | Local Max Pain: ${local_max_pain:.2f} "
                  f"(Diff: {diff:+.2f}, {diff_pct:+.2f}%)")
        )
    else:
        lbl_max_pain.config(
            text=(f"Global Max Pain: ${global_max_pain:.2f} (Diff: {diff:+.2f}, {diff_pct:+.2f}%) "
                  "(No Local Nearby Strike)")
        )

    # --- ATR Logic ---
    atr = calculate_atr(ticker)
    expiration_date = datetime.strptime(expiration, "%Y-%m-%d")
    days_to_expiry = (expiration_date - datetime.now()).days

    if atr is not None and days_to_expiry > 0:
        atr_threshold = atr * (days_to_expiry / 14) ** 0.5

        diff_global = global_max_pain - price
        within_atr_global = abs(diff_global) <= atr_threshold

        if local_max_pain is not None:
            diff_local = local_max_pain - price
            within_atr_local = abs(diff_local) <= atr_threshold
        else:
            diff_local = None
            within_atr_local = False

        atr_text = (
            f"Within ATR - Global: {'Yes ✅' if within_atr_global else 'No ❌'} "
            f"(Diff: {diff_global:+.2f}, ±{atr_threshold:.2f})"
        )
        if local_max_pain is not None:
            atr_text += (
                f" | Local: {'Yes ✅' if within_atr_local else 'No ❌'} "
                f"(Diff: {diff_local:+.2f})"
            )

        lbl_atr.config(text=atr_text)
    else:
        lbl_atr.config(text="Within ATR: Insufficient Data or Expired")

    # Save current state globally for filtering
    current_options_df = options_df
    current_price = price
    current_global_max_pain = global_max_pain
    current_local_max_pain = local_max_pain
    current_ticker = ticker
    current_expiration = expiration

    # Plot initial data with current filter
    plot_filtered_data()

def update_slider_position(current_price):
    global original_xlim, slider
    if original_xlim is None or slider is None:
        return

    x_min, x_max = original_xlim
    x_range = x_max - x_min
    window_frac = 0.25

    frac = (current_price - x_min) / x_range
    left_frac = frac - window_frac / 2
    left_frac = max(0, min(left_frac, 1 - window_frac))

    slider.set(left_frac)
    update_xlim_from_slider(left_frac)

def reset_view():
    global canvas, ax, original_xlim, original_ylim, slider
    if canvas and ax and original_xlim and original_ylim:
        ax.set_xlim(original_xlim)
        ax.set_ylim(original_ylim)
        canvas.draw_idle()
        if slider:
            slider.set(0)

def export_figure():
    global last_fig, last_options_df
    if last_fig is None or last_options_df is None:
        messagebox.showwarning("Warning", "No figure or data to export yet!")
        return

    # Use your specified path
    export_folder = r"C:\Users\jason\OneDrive\Desktop\OptionsAnalytics\data"
    os.makedirs(export_folder, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    img_filename = f"options_plot_{timestamp}.png"
    csv_filename = f"options_data_{timestamp}.csv"

    img_path = os.path.join(export_folder, img_filename)
    csv_path = os.path.join(export_folder, csv_filename)

    last_fig.savefig(img_path)
    last_options_df.to_csv(csv_path, index=False)

    messagebox.showinfo("Exported", f"Chart saved to:\n{img_path}\n\nData saved to:\n{csv_path}")


def update_xlim_from_slider(val):
    global ax, original_xlim, canvas
    if ax is None or original_xlim is None:
        return
    try:
        left_frac = float(val)
    except Exception:
        return

    x_range = original_xlim[1] - original_xlim[0]
    window_frac = 0.25

    if left_frac + window_frac > 1:
        left_frac = 1 - window_frac
    if left_frac < 0:
        left_frac = 0

    new_min = original_xlim[0] + left_frac * x_range
    new_max = new_min + window_frac * x_range

    ax.set_xlim(new_min, new_max)
    if canvas:
        canvas.draw_idle()

# --- GUI SETUP ---

root = tk.Tk()
root.title("Options Max Pain Tracker (yfinance)")
root.geometry("900x740")

frame_top = tk.Frame(root)
frame_top.pack(pady=10)

tk.Label(frame_top, text="Enter Stock Ticker:").pack(side=tk.LEFT, padx=5)
entry_ticker = ttk.Entry(frame_top, width=12)
entry_ticker.pack(side=tk.LEFT, padx=5)

btn_fetch = ttk.Button(frame_top, text="Analyze", command=run_analysis)
btn_fetch.pack(side=tk.LEFT, padx=5)

btn_export = ttk.Button(frame_top, text="Export Chart & Data", command=export_figure)
btn_export.pack(side=tk.LEFT, padx=5)

btn_reset = ttk.Button(frame_top, text="Reset View", command=reset_view)
btn_reset.pack(side=tk.LEFT, padx=5)

# Dropdown filter for All / Calls / Puts
filter_var = tk.StringVar()
filter_combobox = ttk.Combobox(frame_top, textvariable=filter_var, state="readonly", width=10)
filter_combobox['values'] = ("All", "Calls", "Puts")
filter_combobox.current(0)  # default All
filter_combobox.pack(side=tk.LEFT, padx=5)
filter_combobox.bind("<<ComboboxSelected>>", lambda e: plot_filtered_data())

lbl_price = tk.Label(root, text="Current Price: ", font=("Arial", 12))
lbl_price.pack(pady=(10, 0))

lbl_max_pain = tk.Label(root, text="Max Pain Strike: ", font=("Arial", 11))
lbl_max_pain.pack()

lbl_atr = tk.Label(root, text="Within ATR: ", font=("Arial", 11))
lbl_atr.pack()

lbl_expiry = tk.Label(root, text="Using Expiration: ", font=("Arial", 10))
lbl_expiry.pack(pady=(0, 10))

frame_plot = tk.Frame(root)
frame_plot.pack(fill=tk.BOTH, expand=True)

slider = ttk.Scale(root, from_=0, to=1, orient='horizontal', command=update_xlim_from_slider)
slider.pack(fill='x', padx=15, pady=5)
slider.set(0)

root.mainloop()
