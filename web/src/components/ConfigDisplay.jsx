import React, { useState } from 'react'

function ConfigDisplay({ config }) {
  const [collapsed, setCollapsed] = useState(false)

  if (!config) return null

  return (
    <div className="config-display">
      <div className="config-header" onClick={() => setCollapsed(!collapsed)}>
        <h2>Current Configuration</h2>
        <button type="button" className="collapse-btn">
          {collapsed ? '▼' : '▲'}
        </button>
      </div>

      {!collapsed && (
        <div className="config-content">
          <div className="config-section">
            <h3>Model</h3>
            <div className="config-item">
              <span className="config-key">Model:</span>
              <span className="config-value">{config.model.default}</span>
            </div>
            <div className="config-item">
              <span className="config-key">Cache:</span>
              <span className="config-value">{config.model.cache_dir}</span>
            </div>
          </div>

          <div className="config-section">
            <h3>Generation Settings</h3>
            <div className="config-item">
              <span className="config-key">Size:</span>
              <span className="config-value">
                {config.generation.width}x{config.generation.height}
              </span>
            </div>
            <div className="config-item">
              <span className="config-key">Steps:</span>
              <span className="config-value">{config.generation.steps}</span>
            </div>
            <div className="config-item">
              <span className="config-key">Guidance Scale:</span>
              <span className="config-value">{config.generation.guidance_scale}</span>
            </div>
            <div className="config-item">
              <span className="config-key">Negative Prompt:</span>
              <span className="config-value negative-prompt">
                {config.generation.negative_prompt}
              </span>
            </div>
          </div>

          <div className="config-section">
            <h3>Output</h3>
            <div className="config-item">
              <span className="config-key">Directory:</span>
              <span className="config-value">{config.output.directory}</span>
            </div>
            <div className="config-item">
              <span className="config-key">Format:</span>
              <span className="config-value">{config.output.format}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ConfigDisplay
