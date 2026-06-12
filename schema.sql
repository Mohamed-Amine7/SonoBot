-- Database: ecommerce_db
CREATE DATABASE IF NOT EXISTS `ecommerce_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `ecommerce_db`;

-- Table structure for table `products`
DROP TABLE IF EXISTS `products`;
CREATE TABLE `products` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `price` DECIMAL(10,2) NOT NULL,
  `stock` INT NOT NULL DEFAULT 0,
  `category` VARCHAR(100) DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dumping sample data for table `products`
INSERT INTO `products` (`name`, `description`, `price`, `stock`, `category`) VALUES
('Veloce Running Shoes', 'Lightweight and breathable athletic running shoes with advanced shock absorption and ergonomic design. Perfect for marathons or casual daily jogs.', 89.99, 45, 'Footwear'),
('AeroFlow Active T-Shirt', 'Moisture-wicking athletic fit shirt made from recycled polyester. Keeps you cool and dry during intense workouts.', 29.99, 120, 'Apparel'),
('Summit Explorer Backpack', 'Durable water-resistant 40L outdoor travel backpack. Features multiple compartments, a laptop sleeve, and comfortable padded shoulder straps.', 74.50, 18, 'Accessories'),
('SonicBeats Wireless Earbuds', 'True wireless Bluetooth 5.2 earbuds with active noise cancellation, sweat resistance, and a 24-hour battery life charging case.', 59.99, 65, 'Electronics'),
('FlexiCore Yoga Mat', 'Extra-thick 6mm non-slip exercise yoga mat with carrying strap. Made from eco-friendly, non-toxic TPE material.', 35.00, 30, 'Fitness'),
('HydraPeak Stainless Water Bottle', 'Double-wall vacuum insulated water flask (32 oz). Keeps beverages cold for 24 hours or hot for 12 hours.', 24.95, 85, 'Accessories');
