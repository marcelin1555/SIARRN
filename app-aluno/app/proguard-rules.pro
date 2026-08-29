# O app usa org.json e HttpURLConnection, ambos da plataforma, e ZXing só para
# desenhar o QR. Nada aqui depende de reflexão, então as regras padrão bastam.
-keep class com.google.zxing.** { *; }
