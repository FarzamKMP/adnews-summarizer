document.getElementById("load-news").addEventListener("click", async () => {
  const container = document.getElementById("news-container");
  container.innerHTML = "<p>Loading data...</p>";

  try {
    const scrapeRes = await fetch("http://127.0.0.1:8000/api/scrape", {
      method: "POST"
    });
    const scrapeData = await scrapeRes.json();

    container.innerHTML = `<p>Scraping done: found ${scrapeData.found}, inserted ${scrapeData.inserted} articles. Loading news...</p>`;

    const newsRes = await fetch("http://127.0.0.1:8000/api/news");
    const newsData = await newsRes.json();

    container.innerHTML = "";

    newsData.forEach((item) => {
      const pubDate = item.published_at
        ? new Date(item.published_at).toLocaleString("en-US", {
            dateStyle: "medium",
            timeStyle: "short",
          })
        : "Unknown date";

      const div = document.createElement("div");
      div.className = "news-item";
      div.innerHTML = `
        <h3>${item.title}</h3>
        <p class="summary">${item.summary || "No summary available"}</p>
        <div class="meta">
          <small>📅 ${pubDate}</small>
          <small>📰 ${item.source || "Unknown source"}</small>
        </div>
        <a href="${item.url}" target="_blank" class="read-more">Read more →</a>
      `;
      container.appendChild(div);
    });
  } catch (err) {
    container.innerHTML = "<p style='color:red'>Error loading data</p>";
    console.error(err);
  }
});
