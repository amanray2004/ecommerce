const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
import { getKeycloak } from './keycloak'

async function request(path, token, options = {}) {
  const headers = { ...(options.headers || {}) }
  const isFormData = options.body instanceof FormData
  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const doFetch = async (bearerToken) => {
    const reqHeaders = { ...headers }
    if (bearerToken) {
      reqHeaders.Authorization = `Bearer ${bearerToken}`
    }
    try {
      return await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: reqHeaders,
      })
    } catch {
      throw new Error(`Cannot reach backend at ${API_BASE_URL}. Ensure FastAPI is running and CORS is enabled.`)
    }
  }

  const kc = getKeycloak()
  const activeToken = token || kc.token || ''
  let response = await doFetch(activeToken)

  if (response.status === 403) {
    try {
      await kc.updateToken(0)
      response = await doFetch(kc.token || activeToken)
    } catch {
      // Ignore refresh failures and continue with original response handling.
    }
  }

  if (!response.ok) {
    let detail = 'Request failed'
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      detail = response.statusText
    }
    throw new Error(detail)
  }

  if (response.status === 204) return null
  return response.json()
}

export async function fetchProducts({ tenantName, token, search, category, limit = 24, offset = 0 }) {
  const query = new URLSearchParams()
  if (search) query.append('search', search)
  if (category) query.append('category', category)
  query.append('limit', String(limit))
  query.append('offset', String(offset))

  return request(`/${tenantName}/products?${query.toString()}`, token)
}

export async function fetchAllProducts({ token, search, category, limit = 24, offset = 0 }) {
  const query = new URLSearchParams()
  if (search) query.append('search', search)
  if (category) query.append('category', category)
  query.append('limit', String(limit))
  query.append('offset', String(offset))

  return request(`/products?${query.toString()}`, token)
}

export async function createOrder({ tenantName, token, items }) {
  return request(`/${tenantName}/orders`, token, {
    method: 'POST',
    body: JSON.stringify({ items }),
  })
}

export async function fetchOrders({ tenantName, token, limit = 50, offset = 0 }) {
  return request(`/${tenantName}/orders?limit=${limit}&offset=${offset}`, token)
}

export async function fetchAllOrders({ token, limit = 50, offset = 0 }) {
  return request(`/orders?limit=${limit}&offset=${offset}`, token)
}

export async function createProduct({ tenantName, token, formData }) {
  return request(`/${tenantName}/products`, token, {
    method: 'POST',
    body: formData,
  })
}

export async function updateProduct({ tenantName, token, productId, formData }) {
  return request(`/${tenantName}/products/${productId}`, token, {
    method: 'PATCH',
    body: formData,
  })
}

export async function deleteProduct({ tenantName, token, productId }) {
  return request(`/${tenantName}/products/${productId}`, token, {
    method: 'DELETE',
  })
}

export async function fetchFavourites({ tenantName, token }) {
  return request(`/${tenantName}/favourites?limit=100&offset=0`, token)
}

export async function addFavourite({ tenantName, token, productId }) {
  return request(`/${tenantName}/favourites`, token, {
    method: 'POST',
    body: JSON.stringify({ product_id: productId }),
  })
}

export async function removeFavourite({ tenantName, token, productId }) {
  return request(`/${tenantName}/favourites/${productId}`, token, {
    method: 'DELETE',
  })
}

export async function fetchTenants({ token, limit = 100, offset = 0 }) {
  return request(`/admin/tenants?limit=${limit}&offset=${offset}`, token)
}

export async function fetchActiveTenants({ token, limit = 100, offset = 0 }) {
  return request(`/tenants?limit=${limit}&offset=${offset}`, token)
}

export async function createTenant({ token, name }) {
  return request('/admin/tenants', token, {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export async function deleteTenant({ token, tenantId }) {
  return request(`/admin/tenants/${tenantId}`, token, {
    method: 'DELETE',
  })
}

export async function activateTenant({ token, tenantId }) {
  return request(`/admin/tenants/${tenantId}/activate`, token, {
    method: 'PATCH',
  })
}

export async function fetchTenantUsers({ token, tenantName, limit = 100, offset = 0 }) {
  return request(`/admin/tenants/${tenantName}/users?limit=${limit}&offset=${offset}`, token)
}

export async function createTenantUser({ token, tenantName, payload }) {
  return request(`/admin/tenants/${tenantName}/users`, token, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function deleteTenantUser({ token, tenantName, userId }) {
  return request(`/admin/tenants/${tenantName}/users/${userId}`, token, {
    method: 'DELETE',
  })
}

export { API_BASE_URL }
