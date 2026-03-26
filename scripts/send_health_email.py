"""Send system health HTML email to Esam."""
import sys
sys.path.insert(0, "/opt/kovo")
from src.tools.google_api import GoogleAPI

html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#1e293b;border-radius:16px;overflow:hidden;margin-top:20px;margin-bottom:20px;">

  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:30px 32px;">
      <h1 style="margin:0;color:#fff;font-size:24px;">&#x1F5A5;&#xFE0F; KOVO System Health</h1>
      <p style="margin:6px 0 0;color:#c7d2fe;font-size:14px;">March 22, 2026 &#8212; 15:43 GST (UTC+4)</p>
    </td>
  </tr>

  <!-- Overall Status -->
  <tr>
    <td style="padding:24px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#065f46;border-radius:12px;padding:16px 20px;">
        <tr>
          <td style="color:#34d399;font-size:20px;font-weight:700;">&#x2705; All Systems Healthy</td>
        </tr>
        <tr>
          <td style="color:#a7f3d0;font-size:13px;padding-top:4px;">No alerts &#8212; everything within normal thresholds</td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Uptime -->
  <tr>
    <td style="padding:16px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#334155;border-radius:12px;padding:16px 20px;">
        <tr><td style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:1px;">&#x23F1;&#xFE0F; UPTIME</td></tr>
        <tr><td style="color:#f1f5f9;font-size:22px;font-weight:700;padding-top:4px;">10 hours 20 minutes</td></tr>
        <tr><td style="color:#94a3b8;font-size:13px;padding-top:2px;">2 users connected</td></tr>
      </table>
    </td>
  </tr>

  <!-- CPU Load -->
  <tr>
    <td style="padding:16px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#334155;border-radius:12px;padding:16px 20px;">
        <tr><td style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:1px;">&#x26A1; CPU LOAD AVERAGE</td></tr>
        <tr>
          <td style="padding-top:8px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="33%" style="text-align:center;">
                  <div style="color:#f1f5f9;font-size:24px;font-weight:700;">0.39</div>
                  <div style="color:#94a3b8;font-size:11px;">1 min</div>
                </td>
                <td width="33%" style="text-align:center;">
                  <div style="color:#f1f5f9;font-size:24px;font-weight:700;">0.17</div>
                  <div style="color:#94a3b8;font-size:11px;">5 min</div>
                </td>
                <td width="33%" style="text-align:center;">
                  <div style="color:#f1f5f9;font-size:24px;font-weight:700;">0.06</div>
                  <div style="color:#94a3b8;font-size:11px;">15 min</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding-top:10px;">
            <div style="background:#1e293b;border-radius:6px;height:8px;overflow:hidden;">
              <div style="background:#22c55e;height:8px;width:10%;border-radius:6px;"></div>
            </div>
            <div style="color:#22c55e;font-size:11px;padding-top:4px;">Low &#8212; well below 4.0 threshold</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Memory -->
  <tr>
    <td style="padding:16px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#334155;border-radius:12px;padding:16px 20px;">
        <tr><td style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:1px;">&#x1F9E0; MEMORY (RAM)</td></tr>
        <tr>
          <td style="padding-top:8px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="33%" style="text-align:center;">
                  <div style="color:#f1f5f9;font-size:20px;font-weight:700;">1.4 Gi</div>
                  <div style="color:#94a3b8;font-size:11px;">Used</div>
                </td>
                <td width="33%" style="text-align:center;">
                  <div style="color:#f1f5f9;font-size:20px;font-weight:700;">5.9 Gi</div>
                  <div style="color:#94a3b8;font-size:11px;">Available</div>
                </td>
                <td width="33%" style="text-align:center;">
                  <div style="color:#f1f5f9;font-size:20px;font-weight:700;">7.2 Gi</div>
                  <div style="color:#94a3b8;font-size:11px;">Total</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding-top:10px;">
            <div style="background:#1e293b;border-radius:6px;height:8px;overflow:hidden;">
              <div style="background:#22c55e;height:8px;width:19%;border-radius:6px;"></div>
            </div>
            <div style="color:#22c55e;font-size:11px;padding-top:4px;">19% used &#8212; healthy (threshold: 80%)</div>
          </td>
        </tr>
        <tr>
          <td style="padding-top:8px;color:#94a3b8;font-size:12px;">
            &#x1F4BE; Swap: 0 B used / 4.0 Gi total
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Disk -->
  <tr>
    <td style="padding:16px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#334155;border-radius:12px;padding:16px 20px;">
        <tr><td style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:1px;">&#x1F4BF; DISK USAGE</td></tr>
        <tr>
          <td style="padding-top:12px;">
            <table width="100%" cellpadding="4" cellspacing="0">
              <tr style="color:#64748b;font-size:11px;text-transform:uppercase;">
                <td>Mount</td><td>Size</td><td>Used</td><td>Avail</td><td>Use%</td>
              </tr>
              <tr style="color:#f1f5f9;font-size:13px;">
                <td style="padding-top:8px;"><code style="background:#1e293b;padding:2px 6px;border-radius:4px;color:#a78bfa;">/</code></td>
                <td style="padding-top:8px;">28G</td>
                <td style="padding-top:8px;">11G</td>
                <td style="padding-top:8px;">16G</td>
                <td style="padding-top:8px;color:#22c55e;font-weight:700;">41%</td>
              </tr>
              <tr style="color:#f1f5f9;font-size:13px;">
                <td><code style="background:#1e293b;padding:2px 6px;border-radius:4px;color:#a78bfa;">/boot</code></td>
                <td>2.0G</td><td>125M</td><td>1.7G</td>
                <td style="color:#22c55e;font-weight:700;">7%</td>
              </tr>
              <tr style="color:#f1f5f9;font-size:13px;">
                <td><code style="background:#1e293b;padding:2px 6px;border-radius:4px;color:#a78bfa;">/boot/efi</code></td>
                <td>1.1G</td><td>6.3M</td><td>1.1G</td>
                <td style="color:#22c55e;font-weight:700;">1%</td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding-top:10px;">
            <div style="background:#1e293b;border-radius:6px;height:8px;overflow:hidden;">
              <div style="background:#22c55e;height:8px;width:41%;border-radius:6px;"></div>
            </div>
            <div style="color:#22c55e;font-size:11px;padding-top:4px;">Root at 41% &#8212; well below 85% threshold</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Services -->
  <tr>
    <td style="padding:16px 32px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#334155;border-radius:12px;padding:16px 20px;">
        <tr><td style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:1px;">&#x1F433; SERVICES</td></tr>
        <tr>
          <td style="color:#f1f5f9;font-size:13px;padding-top:8px;">
            <span style="color:#fbbf24;">&#x2139;&#xFE0F;</span> Docker is not installed on this VM<br>
            <span style="color:#22c55e;">&#x25CF;</span> KOVO service: <strong>active</strong>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding:24px 32px;text-align:center;border-top:1px solid #334155;">
      <p style="color:#64748b;font-size:11px;margin:0;">
        Generated by <strong style="color:#a78bfa;">KOVO</strong> &#183; Ava, Esam's AI Assistant<br>
        Ubuntu 25.10 (Questing) &#183; 8GB RAM &#183; 50GB Disk
      </p>
    </td>
  </tr>

</table>
</body>
</html>"""

api = GoogleAPI()
result = api.send_email(
    to="time@eim.ae",
    subject="KOVO System Health Report - March 22, 2026",
    body=html,
    html=True,
)
print("Sent!", result)
