import { useEffect, useMemo, useRef, useState } from "react";

function App() {
  const [comic, setComic] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [chapterIndex, setChapterIndex] = useState(0);
  const [theme, setTheme] = useState("dark");
  const [activePanel, setActivePanel] = useState(0);
  const panelRefs = useRef([]);

  useEffect(() => {
    let ignore = false;

    fetch("/asset-manifest.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Manifest request failed: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        if (!ignore) {
          setComic(data);
        }
      })
      .catch((error) => {
        if (!ignore) {
          setLoadError(error.message || "Unable to load comic manifest.");
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  const chapters = comic?.chapters ?? [];
  const chapter = chapters[chapterIndex];
  const isFinishedPages = comic?.format === "finished-comic-pages";

  const progress = useMemo(() => {
    if (!chapter?.panels?.length) return 0;
    return Math.round(((activePanel + 1) / chapter.panels.length) * 100);
  }, [activePanel, chapter]);

  useEffect(() => {
    setActivePanel(0);
    panelRefs.current = [];
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [chapterIndex]);

  useEffect(() => {
    if (!chapter) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

        if (visible?.target?.dataset.index) {
          setActivePanel(Number(visible.target.dataset.index));
        }
      },
      { threshold: [0.35, 0.55, 0.75] },
    );

    panelRefs.current.forEach((node) => {
      if (node) observer.observe(node);
    });

    return () => observer.disconnect();
  }, [chapterIndex, chapter]);

  const goToChapter = (nextIndex) => {
    const bounded = Math.min(Math.max(nextIndex, 0), chapters.length - 1);
    setChapterIndex(bounded);
  };

  if (loadError) {
    return (
      <main className="app" data-format="status" data-theme={theme}>
        <section className="status-panel" role="alert">
          <p className="eyebrow">manifest error</p>
          <h1>漫画数据加载失败</h1>
          <p>{loadError}</p>
        </section>
      </main>
    );
  }

  if (!comic || !chapter) {
    return (
      <main className="app" data-format="status" data-theme={theme}>
        <section className="status-panel" aria-live="polite">
          <p className="eyebrow">loading</p>
          <h1>正在载入漫画章节</h1>
          <p>Loading asset manifest...</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app" data-format={comic.format} data-theme={theme}>
      <div className="progress" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>

      <header className="masthead">
        <div>
          <p className="eyebrow">{comic.format}</p>
          <h1>{comic.title}</h1>
          <p className="subtitle">{comic.subtitle}</p>
          {comic.source ? (
            <a className="source-link" href={comic.source} target="_blank" rel="noreferrer">
              Source repository
            </a>
          ) : null}
        </div>

        <div className="controls" aria-label="Reader controls">
          <label>
            <span>Chapter</span>
            <select
              value={chapter.id}
              onChange={(event) => {
                const next = chapters.findIndex((item) => item.id === event.target.value);
                goToChapter(next);
              }}
            >
              {chapters.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </label>

          <button type="button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <section className="chapter-intro" aria-labelledby="chapter-title">
        <p className="chapter-kicker">Episode {chapterIndex + 1}</p>
        <h2 id="chapter-title">{chapter.title}</h2>
        <p>{chapter.summary}</p>
      </section>

      <section className="reader" aria-label={isFinishedPages ? "Comic pages" : "Comic panels"}>
        {chapter.panels.map((panel, index) => (
          <figure
            className={activePanel === index ? "panel is-active" : "panel"}
            key={panel.id}
            data-index={index}
            ref={(node) => {
              panelRefs.current[index] = node;
            }}
          >
            <img src={panel.image} alt={panel.alt} loading={index === 0 ? "eager" : "lazy"} />
            <figcaption>
              {panel.sfx ? <span className="sfx">{panel.sfx}</span> : null}
              {panel.caption ? <p className="caption">{panel.caption}</p> : null}
              {panel.dialogue?.length ? (
                <div className="dialogue" aria-label="Dialogue">
                  {panel.dialogue.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              ) : null}
            </figcaption>
          </figure>
        ))}
      </section>

      <nav className="chapter-nav" aria-label="Chapter navigation">
        <button type="button" onClick={() => goToChapter(chapterIndex - 1)} disabled={chapterIndex === 0}>
          Previous
        </button>
        <span>{progress}% read</span>
        <button
          type="button"
          onClick={() => goToChapter(chapterIndex + 1)}
          disabled={chapterIndex === chapters.length - 1}
        >
          Next
        </button>
      </nav>
    </main>
  );
}

export default App;
