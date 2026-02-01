import { loadCountriesData } from './map-data.js';

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

    // Load CSS if not already loaded
    this._loadCSS();

    this.innerHTML = `
      <div class="countries-card">
        <div class="card-header">
          <div class="card-title">
            <ha-icon icon="mdi:earth" style="color: ${visitedColor};"></ha-icon>
            ${title}
            <span class="current-badge ${currentCountry ? 'visible' : ''}" style="color: ${currentColor}; background: ${currentColor}15;">
              <ha-icon icon="mdi:map-marker"></ha-icon>
              ${currentCountry || ''}
            </span>
          </div>
          <div class="card-stats" style="background: ${visitedColor}15;"><strong style="color: ${visitedColor};">${visitedCountries.length}</strong> countries</div>
        </div>
        
        <div class="map-container" id="map-container">
          ${this.getWorldMapSVG(countries, visitedCountries, currentCountry, mapColor, visitedColor, currentColor)}
          <div class="tooltip" id="tooltip"></div>
        </div>
        
        ${visitedCountries.length > 0 ? `
        <div class="country-tags">
          ${visitedCountries.map(code => `
            <span class="country-tag ${code === currentCountry ? 'current' : ''}" style="background: ${code === currentCountry ? currentColor + '20' : visitedColor + '20'}; color: ${code === currentCountry ? currentColor : visitedColor};">${code}</span>
          `).join('')}
        </div>
        ` : ''}
        
        <div class="legend">
          <div class="legend-item"><div class="legend-color visited" style="background: ${visitedColor};"></div><span>Visited</span></div>
          <div class="legend-item"><div class="legend-color current" style="background: ${currentColor};"></div><span>Current</span></div>
          <div class="legend-item"><div class="legend-color default" style="background: ${mapColor};"></div><span>Not visited</span></div>
        </div>
      </div>
    `;
    
    this._setupTooltips();
  }

  _loadCSS() {
    if (document.getElementById('countries-map-card-styles')) return;
    
    const link = document.createElement('link');
    link.id = 'countries-map-card-styles';
    link.rel = 'stylesheet';
    link.type = 'text/css';
    
    // Try HACS path first, then module-relative fallback
    const moduleBaseUrl = new URL('.', import.meta.url);
    const cssUrl = new URL('countries-map-card.css', moduleBaseUrl);
    const cssPaths = [
      '/hacsfiles/countries-visited/countries-map-card.css',
      cssUrl.href
    ];
    
    // Try first path, fallback to second if needed
    link.href = cssPaths[0];
    link.onerror = () => {
      link.href = cssPaths[1];
    };
    
    document.head.appendChild(link);
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
    
    const visitedColor = this._config.visited_color || '#4CAF50';
    const currentColor = this._config.current_color || '#FF5722';
    
    container.querySelectorAll('.country').forEach(country => {
      const originalFill = country.getAttribute('fill');
      const isCurrent = country.classList.contains('current');
      const isVisited = country.classList.contains('visited');
      
      country.addEventListener('mouseenter', () => {
        const name = country.getAttribute('title') || country.id;
        tooltip.textContent = isCurrent ? `${name} (Current)` : isVisited ? `${name} (Visited)` : name;
        tooltip.classList.add('visible');
        
        // Darken color on hover
        if (isCurrent) {
          country.setAttribute('fill', this._adjustColor(currentColor, -15));
        } else if (isVisited) {
          country.setAttribute('fill', this._adjustColor(visitedColor, -15));
        }
      });
      
      country.addEventListener('mousemove', (e) => {
        const rect = container.getBoundingClientRect();
        tooltip.style.left = (e.clientX - rect.left) + 'px';
        tooltip.style.top = (e.clientY - rect.top) + 'px';
      });
      
      country.addEventListener('mouseleave', () => {
        tooltip.classList.remove('visible');
        // Restore original color
        country.setAttribute('fill', originalFill);
      });
    });
  }

  getWorldMapSVG(countries, visitedCountries, currentCountry, mapColor, visitedColor, currentColor) {
    return `<svg viewBox="0 0 1000 666" preserveAspectRatio="xMidYMid meet">
      ${countries.map(c => {
        const isCurrent = currentCountry === c.id;
        const isVisited = visitedCountries.includes(c.id);
        let cls = 'country';
        let fill = mapColor;
        let stroke = 'var(--card-background-color, #fff)';
        let strokeWidth = '0.5';
        
        if (isCurrent) {
          cls += ' current';
          fill = currentColor;
          stroke = currentColor;
          strokeWidth = '2';
        } else if (isVisited) {
          cls += ' visited';
          fill = visitedColor;
        }
        
        return `<path id="${c.id}" class="${cls}" d="${c.d}" title="${c.name}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
      }).join('')}
    </svg>`;
  }
}

customElements.define('countries-map-card', CountriesMapCard);

// Register card with Home Assistant's card registry
if (window.customCards) {
  window.customCards.push({
    type: 'countries-map-card',
    name: 'Countries Visited',
    description: 'Interactive world map showing visited countries',
    preview: false,
    documentationURL: 'https://github.com/RorGray/countries-visited'
  });
}

// Also register with HA's internal registry if available
if (window.loadCardHelpers) {
  window.loadCardHelpers().then((helpers) => {
    // Card helpers are loaded, card should be discoverable
    console.log('Countries Visited card registered with Home Assistant');
  });
}
