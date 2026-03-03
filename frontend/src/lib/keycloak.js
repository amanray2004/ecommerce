import Keycloak from 'keycloak-js'

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
})

let initialized = false

export async function initKeycloak() {
  if (initialized) return keycloak.authenticated

  const authenticated = await keycloak.init({
    onLoad: 'check-sso',
    pkceMethod: 'S256',
    checkLoginIframe: false,
  })

  initialized = true
  if (authenticated) {
    setInterval(async () => {
      try {
        await keycloak.updateToken(30)
      } catch {
        keycloak.clearToken()
      }
    }, 20000)
  }

  return authenticated
}

export function getKeycloak() {
  return keycloak
}
