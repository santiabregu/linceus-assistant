#!/bin/sh
# Reemplaza placeholders con variables de entorno en los ficheros HTML/JS
for f in /usr/share/nginx/html/*.html /usr/share/nginx/html/*.js; do
  [ -f "$f" ] || continue
  sed -i "s|__SUPABASE_URL__|${NEXT_PUBLIC_SUPABASE_URL}|g" "$f"
  sed -i "s|__SUPABASE_ANON_KEY__|${NEXT_PUBLIC_SUPABASE_ANON_KEY}|g" "$f"
  sed -i "s|__RASA_SERVER__|${RASA_SERVER:-http://rasa:5005}|g" "$f"
done

exec nginx -g 'daemon off;'
