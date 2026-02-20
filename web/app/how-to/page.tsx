import Link from "next/link";

export const metadata = {
  title: "How To Start A Deal"
};

export default function HowToPage() {
  return (
    <section className="howtoWrap" aria-label="How to use CommonTrust bot">
      <div className="howtoHero">
        <div className="homeKicker">Quick start</div>
        <h1 className="homeTitle">Start with /newdeal, then send the invite link.</h1>
        <p className="homeDek">
          This is the primary action for every new user. Open the bot in DM, run <code>/newdeal your deal
          description</code>, and share the generated invite link with the other person.
        </p>
        <div className="homeCtas">
          <a className="btn btnPrimary" href="https://t.me/commontrust_bot" target="_blank" rel="noreferrer">
            Open CommonTrust Bot
          </a>
          <Link className="pill" href="/reviews">
            Browse completed deals and reviews
          </Link>
        </div>
      </div>

      <div className="howtoGrid">
        <article className="card">
          <h2 className="sectionTitle">Step 1 (required)</h2>
          <p className="howtoStep">
            In DM with the bot, send:
            <br />
            <code>/newdeal Car rental Feb 16-21</code>
          </p>
          <p className="muted">The bot creates a private deal invite link tied to your deal.</p>
        </article>

        <article className="card">
          <h2 className="sectionTitle">Step 2 (required)</h2>
          <p className="howtoStep">Send that generated invite link to the other user.</p>
          <p className="muted">
            When they open it, they accept and confirm the deal with one tap. Do not skip this link-sharing step.
          </p>
        </article>

        <article className="card">
          <h2 className="sectionTitle">Step 3</h2>
          <p className="howtoStep">After the exchange is done, tap “Mark Completed”.</p>
          <p className="muted">Both sides can then leave a rating/review to build public reputation.</p>
        </article>
      </div>
    </section>
  );
}
