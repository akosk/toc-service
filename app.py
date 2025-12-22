from fastapi import FastAPI, UploadFile, File, Response
import tempfile, os

from toc_runner import add_toc_to_pdf  # you create this wrapper

app = FastAPI()

@app.post("/toc")
async def toc(file: UploadFile = File(...)):
  with tempfile.TemporaryDirectory() as td:
    inp = os.path.join(td, "in.pdf")
    out = os.path.join(td, "out.pdf")

    data = await file.read()
    with open(inp, "wb") as f:
      f.write(data)

    add_toc_to_pdf(inp, out)  # calls your existing code

    with open(out, "rb") as f:
      out_bytes = f.read()

  return Response(
    content=out_bytes,
    media_type="application/pdf",
    headers={"Content-Disposition": 'inline; filename="vers_with_toc.pdf"'},
  )
