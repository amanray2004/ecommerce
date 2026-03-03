import { useEffect, useMemo, useState } from 'react'
import {
  addFavourite,
  activateTenant,
  API_BASE_URL,
  createTenant,
  createOrder,
  createProduct,
  deleteTenant,
  deleteProduct,
  fetchActiveTenants,
  fetchAllOrders,
  fetchFavourites,
  fetchAllProducts,
  fetchOrders,
  fetchProducts,
  fetchTenants,
  removeFavourite,
  updateProduct,
} from './lib/api'
import { getKeycloak, initKeycloak } from './lib/keycloak'

const DEFAULT_TENANT = ''

function extractRoles(tokenParsed) {
  const roleSet = new Set()
  const realmRoles = tokenParsed?.realm_access?.roles || []
  realmRoles.forEach((r) => roleSet.add(String(r).toLowerCase()))
  const resourceAccess = tokenParsed?.resource_access || {}
  Object.values(resourceAccess).forEach((clientData) => {
    ;(clientData?.roles || []).forEach((r) => roleSet.add(String(r).toLowerCase()))
  })
  return roleSet
}

function canManageProducts(roleSet) {
  return ['tenant-user', 'tenant_user', 'tenant'].some((r) => roleSet.has(r))
}

function isPlatformAdmin(roleSet) {
  return ['platform-admin', 'platform_admin', 'admin', 'superadmin', 'super-admin'].some((r) => roleSet.has(r))
}

function formatINR(value) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function ProductCard({ product, isFavourite, onToggleFavourite, onAddToCart }) {
  const imageSrc = product.image_url?.startsWith('/uploads') ? `${API_BASE_URL}${product.image_url}` : product.image_url
  return (
    <article className="product-card">
      <div className="product-image-wrap">
        <img className="product-image" src={imageSrc} alt={product.name} />
        <button className={`fav-btn ${isFavourite ? 'active' : ''}`} onClick={() => onToggleFavourite(product)}>
          {isFavourite ? '★' : '☆'}
        </button>
      </div>
      <div className="product-content">
        {product.tenant_name && <p className="product-tenant">{product.tenant_name}</p>}
        <p className="product-category">{product.category}</p>
        <h3>{product.name}</h3>
        <p className="product-description">{product.description || 'No description provided.'}</p>
        <div className="product-footer">
          <strong>{formatINR(product.price)}</strong>
          <span>Stock: {product.quantity}</span>
        </div>
        <button className="add-cart-btn" onClick={() => onAddToCart(product)} disabled={product.quantity <= 0}>
          {product.quantity > 0 ? 'Add to cart' : 'Out of stock'}
        </button>
      </div>
    </article>
  )
}

function App() {
  const [isAuthReady, setIsAuthReady] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [token, setToken] = useState('')

  // Shop context (top bar)
  const [shopTenantName, setShopTenantName] = useState(DEFAULT_TENANT)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')

  // Manage context (separate from shop search context)
  const [manageTenantName, setManageTenantName] = useState(DEFAULT_TENANT)

  const [products, setProducts] = useState([])
  const [favouriteIds, setFavouriteIds] = useState(new Set())
  const [cart, setCart] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [view, setView] = useState('shop')
  const [orders, setOrders] = useState([])
  const [favouriteProducts, setFavouriteProducts] = useState([])

  const [newProduct, setNewProduct] = useState({
    name: '',
    description: '',
    category: '',
    price: '',
    quantity: '',
    image: null,
  })

  const [tenants, setTenants] = useState([])
  const [newTenantName, setNewTenantName] = useState('')
  const [activeTenants, setActiveTenants] = useState([])

  useEffect(() => {
    const boot = async () => {
      try {
        const authenticated = await initKeycloak()
        const kc = getKeycloak()
        setIsAuthenticated(authenticated)
        setToken(kc.token || '')
      } finally {
        setIsAuthReady(true)
      }
    }
    boot()
  }, [])

  const roleSet = useMemo(() => extractRoles(getKeycloak().tokenParsed), [isAuthenticated, token])
  const isManager = useMemo(() => canManageProducts(roleSet), [roleSet])
  const isAdmin = useMemo(() => isPlatformAdmin(roleSet), [roleSet])
  const tokenTenantName = useMemo(() => getKeycloak().tokenParsed?.tenant || getKeycloak().tokenParsed?.tenant_name || '', [isAuthenticated, token])

  const categories = useMemo(() => [...new Set(products.map((p) => p.category))], [products])
  const isAllTenantsMode = !shopTenantName
  const cartItems = useMemo(() => Object.values(cart), [cart])
  const cartSummary = useMemo(() => {
    const totalQuantity = cartItems.reduce((sum, item) => sum + item.quantity, 0)
    const totalAmount = cartItems.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0)
    return { totalQuantity, totalAmount }
  }, [cartItems])

  const loadShopData = async () => {
    if (!token) {
      setError('')
      setProducts([])
      setFavouriteIds(new Set())
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')
    try {
      const productData = shopTenantName
        ? await fetchProducts({ tenantName: shopTenantName, token, search, category })
        : await fetchAllProducts({ token, search, category })
      setProducts(productData.items)
      if (shopTenantName) {
        const favData = await fetchFavourites({ tenantName: shopTenantName, token })
        setFavouriteIds(new Set(favData.items.map((item) => item.id)))
      } else {
        setFavouriteIds(new Set())
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadManageProducts = async () => {
    if (!token || !manageTenantName) {
      setError('Please set a tenant in Tenant Manage panel.')
      setProducts([])
      return
    }

    setLoading(true)
    setError('')
    try {
      const productData = await fetchProducts({ tenantName: manageTenantName, token })
      setProducts(productData.items)
    } catch (err) {
      setError(err.message)
      // Prevent stale products from a previous successful load.
      setProducts([])
    } finally {
      setLoading(false)
    }
  }

  const handleFind = async () => {
    setView('shop')
    await loadShopData()
  }

  const loadOrders = async () => {
    const effectiveTenantName = shopTenantName.trim().toLowerCase()
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const orderData = effectiveTenantName
        ? await fetchOrders({ tenantName: effectiveTenantName, token })
        : await fetchAllOrders({ token })
      setOrders(orderData.items || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadFavouriteProducts = async () => {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const tenantName = shopTenantName.trim().toLowerCase()
      if (tenantName) {
        const data = await fetchFavourites({ tenantName, token })
        setFavouriteProducts(data.items || [])
        setFavouriteIds(new Set((data.items || []).map((item) => item.id)))
        return
      }

      const tenants = activeTenants.map((t) => t.name).filter(Boolean)
      const responses = await Promise.all(
        tenants.map(async (name) => {
          try {
            const res = await fetchFavourites({ tenantName: name, token })
            return (res.items || []).map((item) => ({ ...item, tenant_name: item.tenant_name || name }))
          } catch {
            return []
          }
        }),
      )
      const merged = responses.flat()
      const uniqueById = Array.from(new Map(merged.map((item) => [item.id, item])).values())
      setFavouriteProducts(uniqueById)
      setFavouriteIds(new Set(uniqueById.map((item) => item.id)))
    } catch (err) {
      setError(err.message)
      setFavouriteProducts([])
    } finally {
      setLoading(false)
    }
  }

  const loadTenants = async () => {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const data = await fetchTenants({ token })
      setTenants(data.items || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadActiveTenants = async () => {
    if (!token) return
    try {
      const data = await fetchActiveTenants({ token })
      setActiveTenants(data.items || [])
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      loadActiveTenants()
      if (tokenTenantName) {
        setManageTenantName(tokenTenantName)
      }
      loadShopData()
    }
  }, [isAuthenticated])

  const handleLogin = () => getKeycloak().login({ redirectUri: `${window.location.origin}/` })
  const handleSignup = () => getKeycloak().register({ redirectUri: `${window.location.origin}/` })
  const handleLogout = () => getKeycloak().logout({ redirectUri: `${window.location.origin}/` })

  const handleAddToCart = (product) => {
    const itemTenantName = (product.tenant_name || shopTenantName || '').trim().toLowerCase()
    if (!itemTenantName) {
      setError('Unable to detect product tenant for cart.')
      return
    }
    setCart((prev) => {
      const existing = prev[product.id]
      const nextQty = existing ? existing.quantity + 1 : 1
      const clampedQty = Math.min(nextQty, product.quantity)
      return {
        ...prev,
        [product.id]: {
          productId: product.id,
          tenantName: itemTenantName,
          name: product.name,
          price: Number(product.price),
          quantity: clampedQty,
        },
      }
    })
  }

  const updateCartQuantity = (productId, quantity) => {
    setCart((prev) => {
      if (quantity <= 0) {
        const copy = { ...prev }
        delete copy[productId]
        return copy
      }
      return { ...prev, [productId]: { ...prev[productId], quantity } }
    })
  }

  const toggleFavourite = async (product) => {
    const favouriteTenantName = (shopTenantName || product.tenant_name || '').trim().toLowerCase()
    if (!favouriteTenantName) {
      setError('Unable to determine tenant for this product.')
      return
    }
    try {
      if (favouriteIds.has(product.id)) {
        await removeFavourite({ tenantName: favouriteTenantName, token, productId: product.id })
        setFavouriteIds((prev) => {
          const next = new Set(prev)
          next.delete(product.id)
          return next
        })
        setFavouriteProducts((prev) => prev.filter((p) => p.id !== product.id))
      } else {
        await addFavourite({ tenantName: favouriteTenantName, token, productId: product.id })
        setFavouriteIds((prev) => new Set(prev).add(product.id))
        if (view === 'favourites') {
          setFavouriteProducts((prev) => [product, ...prev])
        }
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const handleCheckout = async () => {
    if (!cartItems.length) return
    setLoading(true)
    setError('')
    try {
      const groupedByTenant = cartItems.reduce((acc, item) => {
        const tenant = (item.tenantName || '').trim().toLowerCase()
        if (!tenant) return acc
        if (!acc[tenant]) acc[tenant] = []
        acc[tenant].push({ product_id: item.productId, quantity: item.quantity })
        return acc
      }, {})

      const tenantNames = Object.keys(groupedByTenant)
      if (!tenantNames.length) {
        setError('Unable to place order: tenant not found for cart items.')
        return
      }

      for (const tenantName of tenantNames) {
        await createOrder({
          tenantName,
          token,
          items: groupedByTenant[tenantName],
        })
      }

      setCart({})
      setSuccess(tenantNames.length > 1 ? 'Orders placed successfully across multiple tenants.' : 'Order placed successfully.')
      await loadShopData()
      if (shopTenantName) await loadOrders()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProduct = async (e) => {
    e.preventDefault()
    if (!manageTenantName) {
      setError('Please set a tenant in Tenant Manage panel.')
      return
    }
    if (!newProduct.image) {
      setError('Image is required for product creation.')
      return
    }

    const formData = new FormData()
    formData.append('name', newProduct.name)
    formData.append('description', newProduct.description)
    formData.append('category', newProduct.category)
    formData.append('price', newProduct.price)
    formData.append('quantity', newProduct.quantity)
    formData.append('image', newProduct.image)

    setLoading(true)
    setError('')
    try {
      await createProduct({ tenantName: manageTenantName, token, formData })
      setSuccess('Product created.')
      setNewProduct({ name: '', description: '', category: '', price: '', quantity: '', image: null })
      await loadManageProducts()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleStockUpdate = async (product, nextQty) => {
    const formData = new FormData()
    formData.append('quantity', String(Math.max(nextQty, 0)))
    try {
      await updateProduct({ tenantName: manageTenantName, token, productId: product.id, formData })
      await loadManageProducts()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeleteProduct = async (productId) => {
    try {
      await deleteProduct({ tenantName: manageTenantName, token, productId })
      setSuccess('Product deleted.')
      await loadManageProducts()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleCreateTenant = async (e) => {
    e.preventDefault()
    if (!newTenantName.trim()) return
    setLoading(true)
    setError('')
    try {
      await createTenant({ token, name: newTenantName.trim() })
      setSuccess('Tenant created.')
      setNewTenantName('')
      await loadTenants()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteTenant = async (tenantId) => {
    setLoading(true)
    setError('')
    try {
      await deleteTenant({ token, tenantId })
      setSuccess('Tenant deactivated.')
      await loadTenants()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleActivateTenant = async (tenantId) => {
    setLoading(true)
    setError('')
    try {
      await activateTenant({ token, tenantId })
      setSuccess('Tenant activated.')
      await loadTenants()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthReady) return <div className="center-screen">Preparing storefront...</div>

  if (!isAuthenticated) {
    return (
      <div className="auth-page">
        <div className="auth-showcase">
          <div className="auth-intro">
            <p className="auth-tag">Multi-tenant commerce demo</p>
            <h1>BeeCart</h1>
            <p className="auth-text">One storefront for every brand, powered by Keycloak login and FastAPI APIs.</p>
            <ul>
              <li>Browse products by tenant and category</li>
              <li>Place orders with stock-safe checkout</li>
              <li>Manage products with tenant role permissions</li>
            </ul>
          </div>
          <div className="auth-card">
            <h2>Welcome back</h2>
            <p>Sign in or create a customer account to continue.</p>
            <div className="auth-actions">
              <button onClick={handleLogin}>Login with Keycloak</button>
              <button className="secondary" onClick={handleSignup}>Sign up</button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="logo">BeeCart</div>
        <div className="search-block">
          <input
            value={shopTenantName}
            onChange={(e) => setShopTenantName(e.target.value.trim())}
            placeholder="Tenant (brand), optional"
          />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search products" />
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
          </select>
          <button className="accent" onClick={handleFind} disabled={loading}>{loading ? 'Loading...' : 'Find'}</button>
        </div>
        <div className="user-block">
          <span>{getKeycloak().tokenParsed?.preferred_username || 'user'}</span>
          <button
            onClick={async () => {
              setError('')
              setView('shop')
              await loadShopData()
            }}
            className={view === 'shop' ? 'pill active' : 'pill'}
          >
            Shop
          </button>
          <button onClick={async () => { setView('favourites'); await loadFavouriteProducts() }} className={view === 'favourites' ? 'pill active' : 'pill'}>My Favourites</button>
          <button onClick={async () => { setView('orders'); await loadOrders() }} className={view === 'orders' ? 'pill active' : 'pill'}>My Orders</button>
          <button onClick={async () => {
            setView('manage')
            if (!isManager) {
              setError('You are not allowed to manage tenant products. Only tenant users can access this section.')
            } else {
              setError('')
              if (tokenTenantName) setManageTenantName(tokenTenantName)
              await loadManageProducts()
            }
          }} className={view === 'manage' ? 'pill active' : 'pill'}>Tenant Manage</button>
          {isAdmin && <button onClick={async () => { setView('admin'); await loadTenants() }} className={view === 'admin' ? 'pill active' : 'pill'}>Admin Dashboard</button>}
          <button onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <section className="hero">
        <h2>Everything your cart needs, from {shopTenantName || 'top brands'}</h2>
        <p>Fast multi-tenant shopping powered by Keycloak + FastAPI.</p>
      </section>

      {error && <div className="notice error">{error}</div>}
      {success && <div className="notice success">{success}</div>}

      {view === 'manage' ? (
        isManager ? (
          <main className="manager-wrap">
            <section className="manager-card">
              <h3>Create Product</h3>
              <div className="context-row">
                <label>Manage Tenant</label>
                <select value={manageTenantName} onChange={(e) => setManageTenantName(e.target.value)} disabled={Boolean(tokenTenantName)}>
                  {!tokenTenantName && <option value="">Select tenant</option>}
                  {(tokenTenantName ? [{ id: tokenTenantName, name: tokenTenantName }] : activeTenants).map((tenant) => (
                    <option key={tenant.id || tenant.name} value={tenant.name}>{tenant.name}</option>
                  ))}
                </select>
              </div>
              <form className="manager-form" onSubmit={handleCreateProduct}>
                <input required placeholder="Name" value={newProduct.name} onChange={(e) => setNewProduct((p) => ({ ...p, name: e.target.value }))} />
                <input placeholder="Description" value={newProduct.description} onChange={(e) => setNewProduct((p) => ({ ...p, description: e.target.value }))} />
                <input required placeholder="Category" value={newProduct.category} onChange={(e) => setNewProduct((p) => ({ ...p, category: e.target.value }))} />
                <input required placeholder="Price" type="number" min="0.01" step="0.01" value={newProduct.price} onChange={(e) => setNewProduct((p) => ({ ...p, price: e.target.value }))} />
                <input required placeholder="Quantity" type="number" min="0" value={newProduct.quantity} onChange={(e) => setNewProduct((p) => ({ ...p, quantity: e.target.value }))} />
                <input required type="file" accept="image/*" onChange={(e) => setNewProduct((p) => ({ ...p, image: e.target.files?.[0] || null }))} />
                <button className="accent" type="submit">Create Product</button>
              </form>
            </section>

            <section className="manager-card">
              <h3>Manage Existing Products</h3>
              <div className="manager-list">
                {products.map((product) => (
                  <div className="manager-row" key={product.id}>
                    <div>
                      <strong>{product.name}</strong>
                      <p>{product.category} • {formatINR(product.price)}</p>
                    </div>
                    <div className="manager-actions">
                      <button onClick={() => handleStockUpdate(product, product.quantity - 1)}>-</button>
                      <span>{product.quantity}</span>
                      <button onClick={() => handleStockUpdate(product, product.quantity + 1)}>+</button>
                      <button className="danger" onClick={() => handleDeleteProduct(product.id)}>Delete</button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </main>
        ) : (
          <main className="orders-wrap">
            <section className="orders-panel">
              <div className="panel-heading"><h3>Tenant Manage</h3></div>
              <p className="muted">You are not allowed to manage tenant products. Only users with the tenant-user role can access this section.</p>
            </section>
          </main>
        )
      ) : view === 'orders' ? (
        <main className="orders-wrap">
          <section className="orders-panel">
            <div className="panel-heading"><h3>My Orders</h3><p>{orders.length} orders</p></div>
            {orders.length === 0 && <p className="muted">{shopTenantName ? 'No orders yet for this tenant.' : 'No orders yet.'}</p>}
            <div className="orders-list">
              {orders.map((order) => (
                <article className="order-card" key={order.id}>
                  <div className="order-top"><strong>Order #{order.id}</strong><span>{new Date(order.created_at).toLocaleString()}</span></div>
                  <div className="order-meta"><span>Total Qty: {order.total_quantity}</span><span>Total Amount: {formatINR(order.total_amount)}</span></div>
                  <div className="order-items">
                    {order.items.map((item) => (
                      <div className="order-item-row" key={item.id}>
                        <span>Product ID: {item.product_id}</span>
                        <span>Qty: {item.quantity}</span>
                        <span>{formatINR(item.price_at_purchase)} each</span>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </main>
      ) : view === 'favourites' ? (
        <main className="main-grid">
          <section className="products-panel">
            <div className="panel-heading"><h3>My Favourites</h3><p>{favouriteProducts.length} items</p></div>
            {favouriteProducts.length === 0 && <p className="muted">{shopTenantName ? 'No favourites for this tenant.' : 'No favourite products yet.'}</p>}
            <div className="product-grid">
              {favouriteProducts.map((product) => (
                <ProductCard key={product.id} product={product} isFavourite={favouriteIds.has(product.id)} onToggleFavourite={toggleFavourite} onAddToCart={handleAddToCart} />
              ))}
            </div>
          </section>
          <aside className="cart-panel">
            <h3>Cart</h3>
            {cartItems.length === 0 && <p className="muted">No items yet.</p>}
            {cartItems.map((item) => (
              <div className="cart-row" key={item.productId}>
                <div><strong>{item.name}</strong><p>{item.tenantName} • {formatINR(item.price)}</p></div>
                <div className="qty-actions">
                  <button onClick={() => updateCartQuantity(item.productId, item.quantity - 1)}>-</button>
                  <span>{item.quantity}</span>
                  <button onClick={() => updateCartQuantity(item.productId, item.quantity + 1)}>+</button>
                </div>
              </div>
            ))}
            <div className="checkout-block">
              <p>Total items: {cartSummary.totalQuantity}</p>
              <p>Total: {formatINR(cartSummary.totalAmount)}</p>
              <button onClick={handleCheckout} disabled={!cartItems.length || loading}>Place order</button>
            </div>
          </aside>
        </main>
      ) : view === 'admin' ? (
        <main className="admin-wrap">
          <section className="admin-card">
            <h3>Tenant Management</h3>
            <form className="manager-form" onSubmit={handleCreateTenant}>
              <input placeholder="New tenant name" value={newTenantName} onChange={(e) => setNewTenantName(e.target.value)} required />
              <button className="accent" type="submit">Create Tenant</button>
            </form>
            <div className="admin-list">
              {tenants.map((tenant) => (
                <div className="admin-row" key={tenant.id}>
                  <div><strong>{tenant.name}</strong><p>{tenant.is_active ? 'Active' : 'Inactive'}</p></div>
                  <div className="admin-actions">
                    {tenant.is_active ? (
                      <button className="danger" onClick={() => handleDeleteTenant(tenant.id)}>Deactivate</button>
                    ) : (
                      <button onClick={() => handleActivateTenant(tenant.id)}>Activate</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </main>
      ) : (
        <main className="main-grid">
          <section className="products-panel">
            <div className="panel-heading"><h3>Products</h3><p>{products.length} items</p></div>
            {isAllTenantsMode && <p className="muted">Showing products from all tenants. Favourites are available only in single-tenant mode.</p>}
            <div className="product-grid">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} isFavourite={favouriteIds.has(product.id)} onToggleFavourite={toggleFavourite} onAddToCart={handleAddToCart} />
              ))}
            </div>
          </section>
          <aside className="cart-panel">
            <h3>Cart</h3>
            {cartItems.length === 0 && <p className="muted">No items yet.</p>}
            {cartItems.map((item) => (
              <div className="cart-row" key={item.productId}>
                <div><strong>{item.name}</strong><p>{item.tenantName} • {formatINR(item.price)}</p></div>
                <div className="qty-actions">
                  <button onClick={() => updateCartQuantity(item.productId, item.quantity - 1)}>-</button>
                  <span>{item.quantity}</span>
                  <button onClick={() => updateCartQuantity(item.productId, item.quantity + 1)}>+</button>
                </div>
              </div>
            ))}
            <div className="checkout-block">
              <p>Total items: {cartSummary.totalQuantity}</p>
              <p>Total: {formatINR(cartSummary.totalAmount)}</p>
              <button onClick={handleCheckout} disabled={!cartItems.length || loading}>Place order</button>
            </div>
          </aside>
        </main>
      )}
    </div>
  )
}

export default App
