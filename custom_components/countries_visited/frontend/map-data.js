// Countries data - loaded from SVG and JSON files
let countriesData = null;

export async function loadCountriesData() {
  if (countriesData) return countriesData;
  try {
    // Try multiple paths for SVG file (absolute for HA, relative for demo)
    // Use import.meta.url to get the current module's location
    const moduleBaseUrl = new URL('.', import.meta.url);
    const dataUrl = new URL('data/world.svg', moduleBaseUrl);
    
    const svgPaths = [
      '/countries_visited/frontend/data/world.svg',  // HA absolute path
      dataUrl.href,  // Relative to module location (works for both file:// and http://)
      '../custom_components/countries_visited/frontend/data/world.svg',  // Demo relative path
      './data/world.svg'  // Fallback
    ];
    
    let svgText = null;
    for (const path of svgPaths) {
      try {
        const response = await fetch(path);
        if (response.ok) {
          svgText = await response.text();
          break;
        }
      } catch (e) {
        continue;
      }
    }
    
    if (!svgText) {
      console.error('Failed to load world.svg from any path. Tried:', svgPaths);
      return [];
    }
    
    // Parse SVG to extract path elements
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(svgText, 'image/svg+xml');
    const paths = svgDoc.querySelectorAll('path');
    
    // Try multiple paths for country info JSON
    const infoUrl = new URL('data/country-info.json', moduleBaseUrl);
    const infoPaths = [
      '/countries_visited/frontend/data/country-info.json',  // HA absolute path
      infoUrl.href,  // Relative to module location (works for both file:// and http://)
      '../custom_components/countries_visited/frontend/data/country-info.json',  // Demo relative path
      './data/country-info.json'  // Fallback
    ];
    
    let countryInfo = {};
    for (const path of infoPaths) {
      try {
        const response = await fetch(path);
        if (response.ok) {
          countryInfo = await response.json();
          break;
        }
      } catch (e) {
        continue;
      }
    }
    
    // Combine SVG path data with country info
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
    console.error('Failed to load countries data:', e);
    return [];
  }
}
