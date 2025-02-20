// client/src/App.jsx
import { useState } from 'react'

function App() {
  const [file, setFile] = useState(null)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
  }

  const handleUpload = async () => {
    if (!file) return

    const formData = new FormData()
    formData.append('video', file)

    try {
      const response = await fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      console.log('Upload successful:', data)
    } catch (error) {
      console.error('Upload failed:', error)
    }
  }

  return (
    <div>
      <h1>Video Uploader</h1>
      <input 
        type="file" 
        accept="video/*,.mkv,video/x-matroska" 
        onChange={handleFileChange}
      />
      <button onClick={handleUpload} disabled={!file}>
        Upload Video
      </button>
      {progress > 0 && (
        <div>
          <progress value={progress} max="100">{progress}%</progress>
          <span>{Math.round(progress)}%</span>
        </div>
      )}
    </div>
  )
}

export default App