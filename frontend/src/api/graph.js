import service, { requestWithRetry } from './index'

/**
 * Generate ontology (upload documents and simulation requirements)
 * @param {Object} data - Contains files, simulation_requirement, project_name, etc.
 * @returns {Promise}
 */
export function generateOntology(formData) {
  return requestWithRetry(() => 
    service({
      url: '/api/graph/ontology/generate',
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  )
}

/**
 * Build knowledge graph
 * @param {Object} data - Contains project_id, graph_name, etc.
 * @returns {Promise}
 */
export function buildGraph(data) {
  return requestWithRetry(() =>
    service({
      url: '/api/graph/build',
      method: 'post',
      data
    })
  )
}

/**
 * Query task status
 * @param {String} taskId - Task ID
 * @returns {Promise}
 */
export function getTaskStatus(taskId) {
  return service({
    url: `/api/graph/task/${taskId}`,
    method: 'get'
  })
}

/**
 * Get graph data
 * @param {String} graphId - Graph ID
 * @returns {Promise}
 */
export function getGraphData(graphId) {
  return service({
    url: `/api/graph/data/${graphId}`,
    method: 'get'
  })
}

/**
 * Get project information
 * @param {String} projectId - Project ID
 * @returns {Promise}
 */
export function getProject(projectId) {
  return service({
    url: `/api/graph/project/${projectId}`,
    method: 'get'
  })
}

/**
 * Fetch a URL and extract its text content for simulation input
 * @param {String} url - The URL to fetch
 * @returns {Promise<{title, text, url, char_count}>}
 */
export function fetchUrl(url) {
  return requestWithRetry(() =>
    service({
      url: '/api/graph/fetch-url',
      method: 'post',
      data: { url }
    })
  )
}

/**
 * US-040 — Fetch entities of a graph grouped by type, used by the
 * Step 1.5 review screen. Wraps GET /api/simulation/entities/{graph_id}.
 *
 * @param {String} graphId
 * @param {Object} [opts]
 * @param {Boolean} [opts.enrich=false] include incident edges (slower).
 * @returns {Promise}
 */
export function getGraphEntities(graphId, { enrich = false } = {}) {
  return service({
    url: `/api/simulation/entities/${graphId}`,
    method: 'get',
    params: { enrich: enrich ? 'true' : 'false' }
  })
}

/**
 * US-040 — Step 1.5 « Review & refine entities ».
 *
 * Apply a user-curated diff (rename / merge / delete / add) on the
 * entities of a freshly built graph, atomically (single Neo4j txn).
 *
 * @param {String} graphId - Target graph UUID.
 * @param {Object} diff
 * @param {Array<{entity_uuid: string, new_name: string}>} [diff.renames]
 * @param {Array<{src_uuid: string, target_uuid: string}>} [diff.merges]
 * @param {Array<{entity_uuid: string}>} [diff.deletes]
 * @param {Array<{name: string, entity_type: string}>} [diff.additions]
 * @returns {Promise}
 */
export function refineEntities(graphId, diff = {}) {
  return requestWithRetry(() =>
    service({
      url: '/api/graph/entities/refine',
      method: 'post',
      data: {
        graph_id: graphId,
        renames: diff.renames || [],
        merges: diff.merges || [],
        deletes: diff.deletes || [],
        additions: diff.additions || [],
      }
    })
  )
}
