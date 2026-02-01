// Countries data - loaded from SVG and JSON files
let countriesData = null;

export async function loadCountriesData() {
  if (countriesData) return countriesData;
  try {
    const svgPath = '/www/community/countries_visited/data/world.svg';  // HA absolute path
    
    let svgText = null;
    try {
      const response = await fetch(svgPath);
      if (response.ok) {
        svgText = await response.text();
      }
    } catch (e) {
      console.error('Failed to load world.svg from:', svgPath, e);
      return [];
    }
    
    if (!svgText) {
      console.error('Failed to load world.svg from:', svgPath);
      return [];
    }
    
    // Parse SVG to extract path elements
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(svgText, 'image/svg+xml');
    const paths = svgDoc.querySelectorAll('path');
    
    const infoPath = '/www/community/countries_visited/data/country-info.json';  // HA absolute path
    const response = await fetch(infoPath);
    const countryInfo = await response.json();
    
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
