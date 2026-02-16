# Setting up SCAT on a new Windows PC

Use this when you have copied the `scat-master` folder (e.g. to `C:\Users\<You>\OneDrive\Desktop\scat-master`) on another Windows PC and want to run the same command line.

## 1. Install Python

- Install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/).
- During setup, enable **“Add Python to PATH”**.
- Confirm in a new Command Prompt or PowerShell:
  ```cmd
  python --version
  ```
  You should see e.g. `Python 3.12.x`.

## 2. Install SCAT and all dependencies

**Option A — Easiest: run the install script**

1. Open the `scat-master` folder in File Explorer.
2. Double-click **`install.bat`**.
3. It will install all dependencies from `requirements.txt`, then install SCAT in editable mode. Use the same Python that you use to run scat (e.g. from python.org).

**Option B — Manual (Command Prompt or PowerShell)**

```cmd
cd C:\Users\<YourUsername>\OneDrive\Desktop\scat-master
```

Replace `<YourUsername>` with your Windows user name.

Install dependencies first, then SCAT:

```cmd
python -m pip install -r requirements.txt
python -m pip install --editable "C:\Users\<YourUsername>\OneDrive\Desktop\scat-master"
```

Use the **full path** to your `scat-master` folder in the second command. If you get “requires 1 arg”, the path in quotes must be the argument to `--editable`.

Optional (faster CRC): after the above, run `pip install libscrc`.

## 3. Find the modem COM port (if using serial)

- Connect the modem (e.g. SIM7600) via USB.
- Open **Device Manager** → **Ports (COM & LPT)**.
- Note the COM port for your modem (e.g. **COM14**). It may be different on this PC (e.g. COM3, COM5).

## 4. Run SCAT

From any directory (or from `scat-master`):

```cmd
python -m scat -t qc -s COM14 --kpi --dl-bandwidth 20 --json-udp-port 9999
```

- Replace **COM14** with the COM port you found in step 3.
- To disable GSMTAP and only send JSON: add `--no-gsmtap`:
  ```cmd
  python -m scat -t qc -s COM14 --kpi --dl-bandwidth 20 --json-udp-port 9999 --no-gsmtap
  ```

**Note:** If you use **serial only** (`-s COMxx`), you do not need PyUSB or libusb. If you use USB mode (`--usb`) or `--list-usb`, you need PyUSB and a Windows libusb backend (e.g. libusb-win32 or Zadig).

## Summary

| Step | Action |
|------|--------|
| 1 | Install Python 3.10+ and add to PATH |
| 2 | Run `install.bat` in scat-master, or: `pip install -r requirements.txt` then `pip install --editable "path"` |
| 3 | Check Device Manager for the modem COM port |
| 4 | Run `python -m scat -t qc -s COMxx --kpi --dl-bandwidth 20 --json-udp-port 9999` |

For more options and KPI details, see [KPI_USAGE.md](KPI_USAGE.md).
