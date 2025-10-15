export async function fetchJSON(url, options = {}) {
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!res.ok) {
      let errorMessage = res.statusText;
      try {
        const errorData = await res.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        const text = await res.text();
        errorMessage = text || errorMessage;
      }
      throw new Error(`${res.status}: ${errorMessage}`);
    }
    
    return res.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Sunucuya bağlanılamıyor. Lütfen backend\'in çalıştığından emin olun.');
    }
    throw error;
  }
}
