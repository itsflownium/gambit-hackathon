# Third-party components

- **Python-chess** (`chess`, >=1.11.2,<2): legal rules, PGN handling, UCI engine integration, and SVG piece rendering. Source and licensing: https://github.com/niklasf/python-chess . Distributed under GPL-3.0-or-later.
- **Chess piece artwork**: Colin M. L. Burnett, via python-chess. Its upstream SVG documentation identifies these pieces as triple licensed under GFDL, BSD and GPL. This project uses the GPL option, consistent with its GPL license. Attribution: https://en.wikipedia.org/wiki/User:Cburnett ; upstream notice: https://python-chess.readthedocs.io/en/latest/svg.html .
- **Stockfish**: a separately installed local engine, not bundled in the plugin source archive. Stockfish 19 source and official releases: https://github.com/official-stockfish/Stockfish/releases/tag/sf_19 . GPL-licensed. The locally installed engine is accompanied by its `Copying.txt` license.
- **HTTPX** (>=0.28.1,<1): public game-export API client. BSD-3-Clause. https://github.com/encode/httpx .
- **React and React DOM**: supplied by Hermes Desktop at runtime. The optional browser preview bundles React for local visual QA. MIT. https://github.com/facebook/react .

Gambit's knight logo and board design were created for this plugin. Gambit source is GPL-3.0-or-later; see `LICENSE`.
