import pytest

INDEX_URL = "https://example.readthedocs.io/en/latest/"

INDEX_HTML = """
<html>
  <body>
    <nav role="navigation"><a href="/">Home</a></nav>
    <div itemprop="articleBody">
      <h1>Example Docs</h1>
      <div class="toctree-wrapper">
        <ul>
          <li><a class="reference internal" href="intro.html">Intro</a></li>
          <li><a class="reference internal" href="guide/usage.html">Usage</a></li>
          <li><a class="reference internal" href="intro.html#section">Intro section</a></li>
          <li><a class="reference external" href="https://other.example.com/x.html">External</a></li>
        </ul>
      </div>
    </div>
  </body>
</html>
"""

PAGE_HTML_TEMPLATE = """
<html>
  <body>
    <script>var x = 1;</script>
    <nav role="navigation">nav junk</nav>
    <div itemprop="articleBody">
      <h1>{title}</h1>
      <p>Some <strong>content</strong>.</p>
      <pre><code>print("hi")</code></pre>
    </div>
  </body>
</html>
"""


@pytest.fixture
def page_html() -> str:
    return PAGE_HTML_TEMPLATE.format(title="A Page")
