"""
Send a sex education report to the owner's email using the existing Google OAuth credentials.
"""
import sys

sys.path.insert(0, "/opt/kovo")

from src.tools.google_api import GoogleAPI

TO = "Time@eim.ae"
SUBJECT = "📋 Comprehensive Report: Human Sexuality — Biology, Health & Relationships"

HTML_BODY = """
<html>
<body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; color: #333;">

<h1 style="color: #2c3e50;">📋 Comprehensive Report: Human Sexuality</h1>
<p style="color: #888; font-size: 13px;">Prepared by Ava — your personal AI assistant | Time@eim.ae</p>
<hr/>

<h2 style="color: #2980b9;">🧬 1. Biology of Sex</h2>
<p>Human sexual reproduction involves the fusion of male (sperm) and female (egg/ovum) gametes, combining genetic material to produce offspring. Key biological aspects include:</p>
<ul>
  <li><strong>Chromosomes:</strong> Biological sex is determined by sex chromosomes — XX (female) and XY (male). Intersex variations (e.g., XXY) are naturally occurring.</li>
  <li><strong>Hormones:</strong> Testosterone, estrogen, and progesterone regulate sexual development, libido, and reproductive cycles.</li>
  <li><strong>Reproductive anatomy:</strong> Male (testes, penis, prostate) and female (ovaries, uterus, vagina) systems serve reproductive roles.</li>
  <li><strong>The menstrual cycle:</strong> A ~28-day hormonal cycle in females preparing the body for potential pregnancy.</li>
  <li><strong>Puberty:</strong> The developmental phase (ages ~8–16) during which sexual maturity is reached, driven by hormonal changes.</li>
</ul>

<h2 style="color: #27ae60;">🏥 2. Sexual Health</h2>
<p>The World Health Organization (WHO) defines sexual health as a state of physical, emotional, mental, and social well-being related to sexuality.</p>
<ul>
  <li><strong>Sexually Transmitted Infections (STIs):</strong> Common STIs include HIV/AIDS, chlamydia, gonorrhoea, syphilis, herpes (HSV), and HPV. Prevention includes condom use, vaccination (HPV, Hepatitis B), and regular testing.</li>
  <li><strong>Contraception methods:</strong>
    <ul>
      <li>Barrier: Condoms (male/female), diaphragm</li>
      <li>Hormonal: Pills, patches, injections, implants</li>
      <li>Long-acting: IUD (intrauterine device)</li>
      <li>Emergency: Morning-after pill (within 72 hours)</li>
      <li>Permanent: Vasectomy, tubal ligation</li>
    </ul>
  </li>
  <li><strong>Regular screening:</strong> Recommended annually for sexually active adults, especially for HIV, STIs, and cervical cancer (Pap smear).</li>
  <li><strong>Sexual dysfunction:</strong> Includes erectile dysfunction, low libido, vaginismus — all treatable with medical or psychological support.</li>
</ul>

<h2 style="color: #8e44ad;">🧠 3. Psychology & Intimacy</h2>
<ul>
  <li><strong>Sexual orientation:</strong> Refers to a person's enduring pattern of attraction — heterosexual, homosexual, bisexual, asexual, and more. Considered a natural spectrum.</li>
  <li><strong>Consent:</strong> Informed, enthusiastic, and ongoing agreement is the cornerstone of ethical sexual interaction. Lack of consent constitutes assault.</li>
  <li><strong>Attachment & intimacy:</strong> Emotional intimacy and secure attachment styles contribute significantly to sexual satisfaction in relationships.</li>
  <li><strong>Mental health link:</strong> Sexual well-being is closely tied to self-esteem, body image, stress levels, and relationship quality.</li>
</ul>

<h2 style="color: #e67e22;">💑 4. Relationships & Communication</h2>
<ul>
  <li><strong>Healthy sexual relationships</strong> are built on mutual respect, open communication, trust, and boundaries.</li>
  <li><strong>Communication tips:</strong> Discussing preferences, boundaries, and concerns openly reduces misunderstandings and increases satisfaction.</li>
  <li><strong>Sexual compatibility</strong> can evolve over time and is not fixed — couples can work through differences with patience and dialogue.</li>
</ul>

<h2 style="color: #c0392b;">🌍 5. Cultural & Social Perspectives</h2>
<ul>
  <li>Attitudes toward sex vary widely across cultures, religions, and historical eras.</li>
  <li>Many societies historically stigmatised sexuality outside of marriage or procreation; modern frameworks increasingly emphasise individual autonomy and consent.</li>
  <li>Islamic perspective (relevant for UAE context): Sex is considered a sacred act within marriage (nikah), and sexual health is encouraged within that framework.</li>
  <li>Media and pornography can create unrealistic expectations — media literacy around sexual content is increasingly important.</li>
</ul>

<h2 style="color: #16a085;">📚 6. Key Takeaways</h2>
<table style="width:100%; border-collapse: collapse;">
  <tr style="background:#f2f2f2;">
    <th style="padding:8px; border:1px solid #ddd;">Area</th>
    <th style="padding:8px; border:1px solid #ddd;">Key Point</th>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd;">Biology</td>
    <td style="padding:8px; border:1px solid #ddd;">Sex is determined by chromosomes, hormones, and anatomy — naturally varies</td>
  </tr>
  <tr style="background:#f9f9f9;">
    <td style="padding:8px; border:1px solid #ddd;">Health</td>
    <td style="padding:8px; border:1px solid #ddd;">Regular STI testing, condom use, and contraception are essential</td>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd;">Psychology</td>
    <td style="padding:8px; border:1px solid #ddd;">Consent and communication are non-negotiable foundations</td>
  </tr>
  <tr style="background:#f9f9f9;">
    <td style="padding:8px; border:1px solid #ddd;">Relationships</td>
    <td style="padding:8px; border:1px solid #ddd;">Emotional intimacy and open dialogue strengthen sexual well-being</td>
  </tr>
  <tr>
    <td style="padding:8px; border:1px solid #ddd;">Culture</td>
    <td style="padding:8px; border:1px solid #ddd;">Context matters — respect cultural and religious norms alongside personal values</td>
  </tr>
</table>

<br/>
<hr/>
<p style="color: #aaa; font-size: 12px;">
  This report was prepared by <strong>Ava</strong>, your AI assistant. For medical advice, always consult a qualified healthcare professional.<br/>
  © 2026 — Ava AI Assistant
</p>

</body>
</html>
"""


def send_report():
    api = GoogleAPI()
    result = api.send_email(to=TO, subject=SUBJECT, body=HTML_BODY, html=True)
    print(f"✅ Email sent to {TO} | message_id: {result['message_id']}")


if __name__ == "__main__":
    send_report()
