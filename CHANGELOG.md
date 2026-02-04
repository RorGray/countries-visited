# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2] - In Progress

### Added
- 🖱️ **Map Controls**: Interactive pan and zoom functionality for the world map
  - Mouse wheel zoom
  - Click and drag panning
  - Touch gesture support (pinch to zoom, drag to pan)
  - Zoom control buttons (+/-) and reset button
  - Zoom indicator showing current zoom level
  - Automatic centering on current country at initial load
- 💬 **Enhanced Tooltips**: Rich country information on hover
  - Country name with status badge (Visited/Current)
  - Region information (Africa, Asia, Europe, etc.)
  - Population data (formatted as 1.4B, 329M, etc.)
  - Sovereignty information
  - Compact, visually appealing design
- 🌐 **German Translations**: Full German language support
  - Config flow translations
  - Card UI translations (legend, tooltips, controls, errors)
  - Region names translated
- 🎛️ **Visual Editors**: Native Home Assistant UI editors
  - Config flow visual editor with color pickers and entity selector
  - Card visual editor with native Home Assistant components
  - Color pickers for all color options
  - Transparent ocean color option with toggle

### Changed
- ✨ Improved card editor UX with native Home Assistant components
- 🎨 Enhanced tooltip styling for better readability
- ⚡ Optimized map rendering performance

### Fixed
- 📐 Card size now configurable through layout tab
- 🐛 Improved error handling and user feedback

## [v0.1] - Initial Release

### Added
- 🌍 Full world map with 250+ countries and territories
- 👤 Multi-person support
- 📊 Automatic country detection from device tracker history
- 🗺️ Reverse geocoding using Nominatim (OpenStreetMap)
- 🔧 Manual country management via services
- 🎨 Customizable colors for map, visited, and current location
- 🎯 Current location highlighting
- 💬 Basic tooltips with country names
- 📈 Geocoding cache statistics sensor
