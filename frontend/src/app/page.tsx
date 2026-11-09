import Link from "next/link";

const benefits = [
  {
    number: "01",
    title: "Find the right lawyer",
    body: "Explore lawyer profiles by city, area of practice, and experience.",
  },
  {
    number: "02",
    title: "Keep matters organized",
    body: "Appointments, case updates, and important documents in one place.",
  },
  {
    number: "03",
    title: "A clearer next step",
    body: "A straightforward way for clients and lawyers to move forward together.",
  },
];

export default function HomePage() {
  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <div>
            <div className="eyebrow">Legal help, closer to home</div>
            <h1>Good counsel can change <em>everything.</em></h1>
            <p className="hero-copy">
              Find a lawyer who understands your needs. Faisla PK brings lawyer
              discovery, consultations, and case updates into one clear experience.
            </p>
            <div className="hero-actions">
              <Link className="button" href="/lawyers">Find a lawyer <span aria-hidden="true">→</span></Link>
              <Link className="button button-outline" href="/register">Create an account</Link>
            </div>
          </div>
          <div className="hero-aside" aria-label="Example lawyer profile">
            <div className="hero-card">
              <div className="hero-card-top">
                <div className="avatar">A</div>
                <div>
                  <strong>Ayesha Khan</strong>
                  <small>Family &amp; civil law · Karachi</small>
                </div>
              </div>
              <span className="verified-pill"><span aria-hidden="true">✓</span> Verified profile</span>
              <div className="hero-card-bottom">
                <span>8 years of experience</span>
                <strong>Browse profiles →</strong>
              </div>
            </div>
            <div className="hero-note">
              <strong>One clear place</strong>
              Cases, appointments &amp; documents
            </div>
          </div>
        </div>
      </section>

      <div className="trust-strip" aria-label="Platform features">
        <span className="trust-label">A more organized legal journey</span>
        <span className="trust-item">Discover</span>
        <span className="trust-item">Connect</span>
        <span className="trust-item">Manage</span>
        <span className="trust-item">Move forward</span>
      </div>

      <section className="section">
        <div className="section-heading">
          <div>
            <div className="eyebrow">The Faisla experience</div>
            <h2>Legal support, without the guesswork.</h2>
          </div>
          <p>Start by finding the right professional, then keep the important details close at hand.</p>
        </div>
        <div className="feature-grid">
          {benefits.map((benefit) => (
            <article className="feature-card" key={benefit.number}>
              <span className="feature-number">{benefit.number}</span>
              <h3>{benefit.title}</h3>
              <p>{benefit.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="cta-panel">
          <div>
            <h2>Your next step starts with a conversation.</h2>
            <p>Search lawyer profiles and find someone suited to your matter.</p>
          </div>
          <Link className="button" href="/lawyers">Explore lawyers <span aria-hidden="true">→</span></Link>
        </div>
      </section>
    </>
  );
}
