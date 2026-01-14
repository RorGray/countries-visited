// Countries data - loaded from JSON file
let countriesData = null;

async function loadCountriesData() {
  if (countriesData) return countriesData;
  try {
    const response = await fetch('/local/community/countries-visited/countries-data.json');
    countriesData = await response.json();
    return countriesData;
  } catch (e) {
    console.error('Failed to load countries data:', e);
    return [];
  }
}

class CountriesMapCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  setConfig(config) {
    this._config = config;
  }

  getConfig() {
    return this._config;
  }

  async render() {
    if (!this._config || !this._hass) return;

    const entity = this._config.entity || this._config.person;
    const visitedColor = this._config.visited_color || '#4CAF50';
    const mapColor = this._config.map_color || '#d0d0d0';
    const currentColor = this._config.current_color || '#FF5722';
    const title = this._config.title || 'Countries Visited';
    
    const stateObj = this._hass.states[entity];
    const visitedCountries = stateObj?.attributes?.visited_countries || [];
    const currentCountry = stateObj?.attributes?.current_country || null;

    // Load countries data
    const countries = await loadCountriesData();

    this.innerHTML = `
      <style>
        .countries-card {
          background: var(--card-background-color, #fff);
          border-radius: 16px;
          padding: 20px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.08);
          font-family: var(--primary-font-family, system-ui);
        }
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid var(--divider-color, #e5e5e5);
        }
        .card-title {
          font-size: 20px;
          font-weight: 600;
          color: var(--primary-text-color, #1a1a1a);
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .card-title ha-icon { color: ${visitedColor}; }
        .card-stats {
          font-size: 14px;
          color: var(--secondary-text-color, #666);
          background: ${visitedColor}15;
          padding: 8px 16px;
          border-radius: 20px;
        }
        .card-stats strong {
          color: ${visitedColor};
          font-size: 18px;
          font-weight: 700;
        }
        .current-badge {
          font-size: 12px;
          color: ${currentColor};
          background: ${currentColor}15;
          padding: 4px 10px;
          border-radius: 12px;
          margin-left: 8px;
          display: ${currentCountry ? 'inline-flex' : 'none'};
          align-items: center;
          gap: 4px;
        }
        .map-container {
          width: 100%;
          background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
          border-radius: 12px;
          overflow: hidden;
        }
        .map-container svg { width: 100%; height: auto; display: block; }
        .country {
          fill: ${mapColor};
          stroke: var(--card-background-color, #fff);
          stroke-width: 0.5;
          transition: fill 0.3s ease, opacity 0.2s ease, stroke-width 0.2s ease;
          cursor: pointer;
        }
        .country.visited { fill: ${visitedColor}; }
        .country.current {
          fill: ${currentColor};
          stroke: ${currentColor};
          stroke-width: 2;
          animation: pulse-border 2s infinite;
        }
        .country:hover {
          opacity: 0.85;
          stroke-width: 1;
          filter: brightness(1.1);
        }
        .country.visited:hover { fill: ${this._adjustColor(visitedColor, -15)}; }
        .country.current:hover { fill: ${this._adjustColor(currentColor, -15)}; }
        @keyframes pulse-border {
          0%, 100% { stroke-width: 2; }
          50% { stroke-width: 3; }
        }
        .tooltip {
          position: absolute;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #1a1a1a);
          padding: 6px 10px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 500;
          box-shadow: 0 2px 8px rgba(0,0,0,0.15);
          pointer-events: none;
          opacity: 0;
          transition: opacity 0.2s ease;
          z-index: 100;
          transform: translate(-50%, -100%);
          margin-top: -8px;
        }
        .tooltip.visible { opacity: 1; }
        .legend {
          display: flex;
          gap: 16px;
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color, #e5e5e5);
          font-size: 12px;
          color: var(--secondary-text-color, #666);
          flex-wrap: wrap;
        }
        .legend-item { display: flex; align-items: center; gap: 6px; }
        .legend-color { width: 16px; height: 10px; border-radius: 2px; }
        .legend-color.visited { background: ${visitedColor}; }
        .legend-color.current { background: ${currentColor}; }
        .legend-color.default { background: ${mapColor}; }
        .country-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 12px;
        }
        .country-tag {
          background: ${visitedColor}20;
          color: ${visitedColor};
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }
        .country-tag.current {
          background: ${currentColor}20;
          color: ${currentColor};
        }
      </style>
      
      <div class="countries-card">
        <div class="card-header">
          <div class="card-title">
            <ha-icon icon="mdi:earth"></ha-icon>
            ${title}
            <span class="current-badge">
              <ha-icon icon="mdi:map-marker"></ha-icon>
              ${currentCountry || ''}
            </span>
          </div>
          <div class="card-stats"><strong>${visitedCountries.length}</strong> countries</div>
        </div>
        
        <div class="map-container" id="map-container">
          ${this.getWorldMapSVG(countries, visitedCountries, currentCountry)}
          <div class="tooltip" id="tooltip"></div>
        </div>
        
        ${visitedCountries.length > 0 ? `
        <div class="country-tags">
          ${visitedCountries.map(code => `
            <span class="country-tag ${code === currentCountry ? 'current' : ''}">${code}</span>
          `).join('')}
        </div>
        ` : ''}
        
        <div class="legend">
          <div class="legend-item"><div class="legend-color visited"></div><span>Visited</span></div>
          <div class="legend-item"><div class="legend-color current"></div><span>Current</span></div>
          <div class="legend-item"><div class="legend-color default"></div><span>Not visited</span></div>
        </div>
      </div>
    `;
    
    this._setupTooltips();
  }

  _adjustColor(color, amount) {
    const hex = color.replace('#', '');
    const r = Math.max(0, Math.min(255, parseInt(hex.substr(0, 2), 16) + amount));
    const g = Math.max(0, Math.min(255, parseInt(hex.substr(2, 2), 16) + amount));
    const b = Math.max(0, Math.min(255, parseInt(hex.substr(4, 2), 16) + amount));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }

  _setupTooltips() {
    const container = this.querySelector('#map-container');
    const tooltip = this.querySelector('#tooltip');
    if (!container || !tooltip) return;
    
    container.querySelectorAll('.country').forEach(country => {
      country.addEventListener('mouseenter', () => {
        const name = country.getAttribute('title') || country.id;
        const isCurrent = country.classList.contains('current');
        const isVisited = country.classList.contains('visited');
        tooltip.textContent = isCurrent ? `${name} (Current)` : isVisited ? `${name} (Visited)` : name;
        tooltip.classList.add('visible');
      });
      country.addEventListener('mousemove', (e) => {
        const rect = container.getBoundingClientRect();
        tooltip.style.left = (e.clientX - rect.left) + 'px';
        tooltip.style.top = (e.clientY - rect.top) + 'px';
      });
      country.addEventListener('mouseleave', () => tooltip.classList.remove('visible'));
    });
  }

  getWorldMapSVG(countries, visitedCountries, currentCountry) {
    return `<svg viewBox="0 0 1000 500" preserveAspectRatio="xMidYMid meet">
      ${countries.map(c => {
        const isCurrent = currentCountry === c.id;
        const isVisited = visitedCountries.includes(c.id);
        let cls = 'country';
        if (isCurrent) cls += ' current';
        else if (isVisited) cls += ' visited';
        return `<path id="${c.id}" class="${cls}" d="${c.d}" title="${c.name}"/>`;
      }).join('')}
    </svg>`;
  }
}

customElements.define('countries-map-card', CountriesMapCard);</parameter>