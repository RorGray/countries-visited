// Countries data - loaded from SVG and JSON files
let countriesData = null;
let _dataLoadLogged = false;

// Styled console logging helper
const logStyle = {
  info: 'color: #4CAF50; font-weight: bold;',
  warn: 'color: #FF9800; font-weight: bold;',
  error: 'color: #F44336; font-weight: bold;',
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

export async function loadCountriesData() {
  if (countriesData) return countriesData;
  try {
    // Try paths for SVG file (HACS path and module-relative fallback)
    // Use import.meta.url to get the current module's location
    const moduleBaseUrl = new URL('.', import.meta.url);
    const dataUrl = new URL('data/world.svg', moduleBaseUrl);
    
    const svgPaths = [
      '/hacsfiles/countries-visited/data/world.svg',  // HACS path
      dataUrl.href  // Relative to module location (fallback)
    ];
    
    let svgText = null;
    let lastError = null;
    for (const path of svgPaths) {
      try {
        const response = await fetch(path);
        if (response.ok) {
          svgText = await response.text();
          if (!_dataLoadLogged) {
            logInfo('Map data loaded successfully');
            _dataLoadLogged = true;
          }
          break;
        } else {
          lastError = `Status ${response.status} from ${path}`;
        }
      } catch (e) {
        lastError = `Error loading ${path}: ${e.message}`;
        continue;
      }
    }
    
    if (!svgText) {
      logError('Failed to load world map data', lastError);
      return [];
    }
    
    // Parse SVG to extract path elements
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(svgText, 'image/svg+xml');
    const paths = svgDoc.querySelectorAll('path');
    
    // Try multiple paths for country info JSON
    const infoUrl = new URL('data/country-info.json', moduleBaseUrl);
    const infoPaths = [
      '/hacsfiles/countries-visited/data/country-info.json',  // HACS path
      infoUrl.href  // Relative to module location (fallback)
    ];
    
    let countryInfo = {};
    let lastInfoError = null;
    for (const path of infoPaths) {
      try {
        const response = await fetch(path);
        if (response.ok) {
          countryInfo = await response.json();
          break;
        } else {
          lastInfoError = `Status ${response.status} from ${path}`;
        }
      } catch (e) {
        lastInfoError = `Error loading ${path}: ${e.message}`;
        continue;
      }
    }
    
    if (Object.keys(countryInfo).length === 0) {
      logWarn('Country info not loaded, using SVG titles only', lastInfoError);
    }
    
    countriesData = Array.from(paths).map(path => {
      const id = path.getAttribute('id');
      const d = path.getAttribute('d');
      const title = path.getAttribute('title') || '';
      
      // Get country name from country-info.json, fallback to title from SVG
      const info = countryInfo[id];
      const name = info?.name || title || id;
      
      return {
        id: id,
        d: d,
        name: name
      };
    }).filter(c => c.id && c.d); // Filter out invalid entries
    
    return countriesData;
  } catch (e) {
    logError('Failed to load countries data', e);
    return [];
  }
}
