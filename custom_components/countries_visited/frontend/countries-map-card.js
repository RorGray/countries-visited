// Card version
const CARD_VERSION = '0.1';

// Dynamic import for map-data.js with version tag
async function loadMapDataModule() {
  const moduleBaseUrl = new URL('.', import.meta.url);
  const mapDataUrl = new URL('map-data.js', moduleBaseUrl);
  const mapDataPaths = [
    `/hacsfiles/countries-visited/map-data.js?v=${CARD_VERSION}`,
    `${mapDataUrl.href}?v=${CARD_VERSION}`
  ];

  // Try each path until one succeeds
  for (const path of mapDataPaths) {
    try {
      const module = await import(path);
      return module;
    } catch (error) {
      // Try next path
      continue;
    }
  }

  // Fallback to relative import without version (for development)
  return import('./map-data.js');
}

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
let _sensorErrorThrown = new Set(); // Track thrown errors to prevent duplicates
let _versionLogged = false;

// CSS loading state (module-level, shared across all card instances)
let _cssLoading = false;
let _cssLoaded = false;
let _cssLoadPromise = null;
let _cssText = null; // Store CSS text once loaded

// Module-level CSS loading function (shared across all card instances)
function loadCardCSS() {
  // If already loaded, return immediately
  if (_cssLoaded && _cssText) {
    return Promise.resolve(_cssText);
  }

  // If currently loading, return the existing promise
  if (_cssLoading && _cssLoadPromise) {
    return _cssLoadPromise;
  }

  // Start loading
  _cssLoading = true;

  _cssLoadPromise = new Promise(async (resolve, reject) => {
    // Try HACS path first, then module-relative fallback
    const moduleBaseUrl = new URL('.', import.meta.url);
    const cssUrl = new URL('countries-map-card.css', moduleBaseUrl);
    const cssPaths = [
      `/hacsfiles/countries-visited/countries-map-card.css?v=${CARD_VERSION}`,
      `${cssUrl.href}?v=${CARD_VERSION}`
    ];

    let cssText = null;
    let lastError = null;

    // Try each path until one succeeds
    for (const path of cssPaths) {
      try {
        const response = await fetch(path);
        if (response.ok) {
          cssText = await response.text();
          break; // Success, exit loop
        } else {
          lastError = `Status ${response.status} from ${path}`;
        }
      } catch (error) {
        lastError = `Error loading ${path}: ${error.message}`;
        continue; // Try next path
      }
    }

    if (!cssText) {
      _cssLoading = false;
      _cssLoadPromise = null;
      reject(new Error(`Failed to load CSS from all paths. Last error: ${lastError}`));
      return;
    }

    // Store CSS text for reuse
    _cssText = cssText;
    _cssLoaded = true;
    _cssLoading = false;
    _cssLoadPromise = null;
    resolve(cssText);
  });

  return _cssLoadPromise;
}

class CountriesMapCard extends HTMLElement {
  constructor() {
    super();
    // Store last rendered state to detect changes
    this._lastState = null;
    this._lastConfig = null;
    // Track if style tag has been added to this card instance
    this._styleTagAdded = false;
  }

  set hass(hass) {
    this._hass = hass;
    // Only render if relevant data has changed
    if (this._shouldUpdate()) {
      this.render();
    }
  }

  setConfig(config) {
    const configChanged = JSON.stringify(this._lastConfig) !== JSON.stringify(config);
    this._config = config;

    // Log version on first config set
    if (!_versionLogged) {
      logVersion();
      _versionLogged = true;
    }

    // If config changed, force a render
    if (configChanged) {
      this._lastConfig = JSON.parse(JSON.stringify(config));
      if (this._hass) {
        this.render();
      }
    }
  }

  getConfig() {
    return this._config;
  }

  _shouldUpdate() {
    if (!this._config || !this._hass) return false;

    let entity = this._config.entity || this._config.person;

    // If entity is a person entity, find the sensor entity
    if (entity && entity.startsWith('person.')) {
      const personEntity = entity;
      const allSensors = Object.keys(this._hass.states)
        .filter(id => id.startsWith('sensor.countries_visited_'))
        .map(id => {
          const state = this._hass.states[id];
          return {
            id,
            person: state?.attributes?.person,
          };
        });

      const sensorEntityId = allSensors.find(s => s.person === personEntity)?.id ||
        allSensors.find(s => s.person?.toLowerCase() === personEntity.toLowerCase())?.id;

      if (sensorEntityId) {
        entity = sensorEntityId;
      } else {
        // Can't find sensor, but might be first render - allow it
        return !this._lastState;
      }
    }

    const stateObj = this._hass.states[entity];
    if (!stateObj) return false;

    const visitedCountries = stateObj?.attributes?.visited_countries || [];
    const currentCountry = stateObj?.attributes?.current_country || null;
    const stateValue = stateObj?.state;

    // Create current state signature
    const currentState = {
      visitedCountries: JSON.stringify(visitedCountries.sort()),
      currentCountry: currentCountry,
      stateValue: stateValue,
      entity: entity
    };

    // Compare with last state
    if (!this._lastState) {
      this._lastState = currentState;
      return true; // First render
    }

    // Check if anything relevant changed
    const hasChanged =
      this._lastState.visitedCountries !== currentState.visitedCountries ||
      this._lastState.currentCountry !== currentState.currentCountry ||
      this._lastState.stateValue !== currentState.stateValue ||
      this._lastState.entity !== currentState.entity;

    if (hasChanged) {
      this._lastState = currentState;
      return true;
    }

    return false; // No relevant changes, skip render
  }

  async render() {
    if (!this._config || !this._hass) return;

    // Load CSS and inject style tag into this card (only once per card instance)
    if (!this._styleTagAdded) {
      try {
        const cssText = await loadCardCSS();
        // Create and inject style tag into this card element
        const styleTag = document.createElement('style');
        styleTag.type = 'text/css';
        styleTag.textContent = cssText;
        // Insert at the beginning of the card
        this.insertBefore(styleTag, this.firstChild);
        this._styleTagAdded = true;
      } catch (error) {
        logWarn('CSS failed to load, card may appear unstyled:', error);
        // Continue anyway - card should still work, just without styling
      }
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

        // Only throw error once per person entity to prevent console spam
        // Show a user-friendly message in the card instead of throwing repeatedly
        if (!_sensorErrorThrown.has(errorKey)) {
          _sensorErrorThrown.add(errorKey);

          // Short, user-friendly error message
          const sensorCount = allSensors.length;
          const errorMsg = sensorCount > 0
            ? `Could not find sensor for person: ${personEntity}. Found ${sensorCount} sensor(s), but none match this person. Please check the integration configuration.`
            : `Could not find sensor for person: ${personEntity}. No sensor entities found. Please install and configure the Countries Visited integration.`;

          throw new Error(errorMsg);
        }

        // If error was already thrown, show a simple message in the card instead
        // Preserve the style tag when setting innerHTML
        const existingStyleTag = this.querySelector('style');
        const styleTagContent = existingStyleTag ? existingStyleTag.outerHTML : '';

        this.innerHTML = styleTagContent + `
          <div class="countries-card">
            <div class="card-header">
              <div class="card-title">Countries Visited</div>
            </div>
            <div style="padding: 20px; text-align: center; color: #888;">
              <p><strong>Sensor not found</strong></p>
              <p>Could not find sensor entity for person: <code>${personEntity}</code></p>
              <p style="font-size: 0.9em; margin-top: 10px;">Please configure the Countries Visited integration for this person.</p>
            </div>
          </div>
        `;
        return;
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

    // Load countries data (with version tag)
    const mapDataModule = await loadMapDataModule();
    const countries = await mapDataModule.loadCountriesData();

    // Preserve the style tag when setting innerHTML
    const existingStyleTag = this.querySelector('style');
    const styleTagContent = existingStyleTag ? existingStyleTag.outerHTML : '';

    this.innerHTML = styleTagContent + `
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

    // Update last state after rendering to track what was rendered
    if (stateObj) {
      this._lastState = {
        visitedCountries: JSON.stringify(visitedCountries.sort()),
        currentCountry: currentCountry,
        stateValue: stateObj.state,
        entity: entity
      };
    }
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
