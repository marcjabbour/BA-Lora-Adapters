export const Header = () => {
  return (
    <header className="border-b bg-white">
      <div className="container mx-auto px-8 py-4">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          LoRA Training Pipeline
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Build and test custom LoRA adapters from customer transcripts
        </p>
      </div>
    </header>
  )
}
