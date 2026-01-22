import { motion } from 'framer-motion'

interface AnimatedWireProps {
  active: boolean      // Green if previous step completed
  blinking: boolean    // Blinking if current step running
}

export const AnimatedWire = ({ active, blinking }: AnimatedWireProps) => {
  return (
    <motion.div
      className={`w-1 h-16 rounded-full transition-colors duration-500 ${
        active ? 'bg-green-500' : 'bg-gray-300'
      }`}
      animate={blinking ? { opacity: [1, 0.3, 1] } : { opacity: 1 }}
      transition={blinking ? { duration: 1.5, repeat: Infinity } : {}}
    />
  )
}
