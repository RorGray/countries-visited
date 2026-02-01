import { loadCountriesData } from './map-data.js';

// Card version
const CARD_VERSION = '0.1';

// Styled console logging helper
const logStyle = {
  info: 'color: #4CAF50; font-weight: bold;',
  warn: 'color: #FF9800; font-weight: bold;',
  error: 'color: #F44336; font-weight: bold;',
  debug: 'color: #2196F3; font-weight: bold;',
  version: 'color: #2196F3; font-weight: bold; background: #E3F2FD; padding: 2px 6px; border-radius: 3px;',
};

function logInfo(message, ...args) {
  console.log(`%c🌍 Countries Visited ${message}`, logStyle.info, ...args);
}

function logWarn(message, ...args) {
  console.warn(`%c🌍 Countries Visited ${message}`, logStyle.warn, ...args);
}

function logError(message, ...args) {
  console.error(`%c🌍 Countries Visited ${message}`, logStyle.error, ...args);
}

function logVersion() {
  console.log(`%c🌍 Countries Visited Card v${CARD_VERSION}`, logStyle.version);
}

// Track if we've already logged sensor finding errors to avoid spam
let _sensorErrorLogged = new Set();
let _versionLogged = false;

class CountriesMapCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  setConfig(config) {
    this._config = config;
    
    // Log version on first config set
    if (!_versionLogged) {
      logVersion();
      _versionLogged = true;
    }
  }

  getConfig() {
    return this._config;
  }

  async render() {
    if (!this._config || !this._hass) return;

    // Wait for CSS to load before rendering to ensure styling is applied
    try {
      await this._loadCSS();
    } catch (error) {
      logWarn('CSS failed to load, card may appear unstyled:', error);
      // Continue anyway - card should still work, just without styling
    }

    let entity = this._config.entity || this._config.person;
    
    // If entity is a person entity, automatically find the corresponding sensor entity
    if (entity && entity.startsWith('person.')) {
      const personEntity = entity;
      
      // Find the sensor entity for this person
      // The sensor entity has the person entity ID in its attributes
      const allSensors = Object.keys(this._hass.states)
        .filter(id => id.startsWith('sensor.countries_visited_'))
        .map(id => {
          const state = this._hass.states[id];
          return {
            id,
            state: state,
            exists: !!state,
            person: state?.attributes?.person,
            hasAttributes: !!state?.attributes,
            visitedCountries: state?.attributes?.visited_countries || [],
            stateValue: state?.state,
            allAttributes: state?.attributes || {}
          };
        });
      
      // Try exact match first
      let sensorEntityId = allSensors.find(s => s.person === personEntity)?.id;
      let matchType = sensorEntityId ? 'exact' : null;
      
      // If not found, try case-insensitive match
      if (!sensorEntityId) {
        const personLower = personEntity.toLowerCase();
        const match = allSensors.find(s => s.person?.toLowerCase() === personLower);
        if (match) {
          sensorEntityId = match.id;
          matchType = 'case-insensitive';
        }
      }
      
      if (sensorEntityId) {
        entity = sensorEntityId;
        // Don't log successful finds - too verbose on every render
        // Only log once on first successful find
        if (!this._sensorFoundLogged) {
          this._sensorFoundLogged = true;
        }
      } else {
        // Only log error once per person entity to avoid spam
        const errorKey = `sensor_error_${personEntity}`;
        if (!_sensorErrorLogged.has(errorKey)) {
          _sensorErrorLogged.add(errorKey);
          
          // Detailed error logging for debugging (only once)
          const debugInfo = {
            searchingFor: personEntity,
            totalSensorsFound: allSensors.length,
            sensors: allSensors.map(s => ({
              entityId: s.id,
              exists: s.exists,
              personAttribute: s.person,
              personAttributeType: typeof s.person,
              personMatches: s.person === personEntity,
              personMatchesCaseInsensitive: s.person?.toLowerCase() === personEntity.toLowerCase(),
              hasAttributes: s.hasAttributes,
              visitedCountriesCount: s.visitedCountries?.length || 0,
              stateValue: s.stateValue
            }))
          };
          
          logError('Could not find sensor entity for person', {
            searchingFor: personEntity,
            totalSensorsFound: allSensors.length,
            availableSensors: allSensors.map(s => `${s.id} (person: ${s.person || 'none'})`),
            debug: debugInfo
          });
        }
        
        // Throw error so Home Assistant displays it properly
        // This is better than showing custom HTML, especially during startup
        const availableSensors = allSensors.length > 0
          ? `\n\nAvailable sensors:\n${allSensors.map(s => `  - ${s.id} (person: ${s.person || 'none'})`).join('\n')}`
          : '\n\nNo sensor entities found. Make sure the Countries Visited integration is installed and configured.';
        
        throw new Error(
          `Could not find sensor entity for person: ${personEntity}. ` +
          `Please make sure the Countries Visited integration is configured for this person.${availableSensors}`
        );
      }
    }
    
    const visitedColor = this._config.visited_color || '#4CAF50';
    const mapColor = this._config.map_color || '#d0d0d0';
    const currentColor = this._config.current_color || '#FF5722';
    const title = this._config.title || 'Countries Visited';
    
    const stateObj = this._hass.states[entity];
    
    // If entity doesn't exist, throw error for Home Assistant to display
    if (!stateObj) {
      throw new Error(`Entity ${entity} not found. Make sure the Countries Visited integration is configured.`);
    }
    
    const visitedCountries = stateObj?.attributes?.visited_countries || [];
    const currentCountry = stateObj?.attributes?.current_country || null;

    // Load countries data
    const countries = await loadCountriesData();

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
    // Check if already loaded
    const existingLink = document.getElementById('countries-map-card-styles');
    if (existingLink && existingLink.sheet) {
      return Promise.resolve(); // Already loaded and parsed
    }
    
    // If link exists but not loaded yet, return existing promise
    if (existingLink && existingLink._loadPromise) {
      return existingLink._loadPromise;
    }
    
    return new Promise((resolve, reject) => {
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
      
      let currentPathIndex = 0;
      let timeoutId = null;
      
      const tryLoad = (pathIndex) => {
        if (pathIndex >= cssPaths.length) {
          if (timeoutId) clearTimeout(timeoutId);
          link._loadPromise = null;
          reject(new Error('Failed to load CSS from all paths'));
          return;
        }
        
        link.href = cssPaths[pathIndex];
        
        // Set up timeout (5 seconds per path)
        timeoutId = setTimeout(() => {
          if (pathIndex < cssPaths.length - 1) {
            // Try next path
            tryLoad(pathIndex + 1);
          } else {
            // All paths failed
            link._loadPromise = null;
            reject(new Error('CSS loading timeout'));
          }
        }, 5000);
        
        // Success handler
        link.onload = () => {
          if (timeoutId) clearTimeout(timeoutId);
          link._loadPromise = null;
          resolve();
        };
        
        // Error handler - try next path
        link.onerror = () => {
          if (timeoutId) clearTimeout(timeoutId);
          tryLoad(pathIndex + 1);
        };
      };
      
      // Store promise on link element to prevent duplicate loads
      link._loadPromise = Promise.resolve();
      
      document.head.appendChild(link);
      tryLoad(0);
    });
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
    icon: '/hacsfiles/countries-visited/icon.svg',
    documentationURL: 'https://github.com/RorGray/countries-visited'
  });
}

// Also register with HA's internal registry if available
if (window.loadCardHelpers) {
  window.loadCardHelpers().then((helpers) => {
    // Card helpers are loaded, card should be discoverable
    if (!_versionLogged) {
      logVersion();
      _versionLogged = true;
    }
  });
}
