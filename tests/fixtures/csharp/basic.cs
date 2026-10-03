using System;

class Program
{
    static void Main(string[] args)
    {
        Console.WriteLine("Введите число:");
        int x = int.Parse(Console.ReadLine());
        if (x > 0)
        {
            Console.WriteLine("positive");
        }
        else if (x < 0)
        {
            Console.WriteLine("negative");
        }
        else
        {
            Console.WriteLine("zero");
        }
    }
}
