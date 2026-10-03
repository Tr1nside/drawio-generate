using System;

class Helpers
{
    static void Main(string[] args)
    {
        int x = int.Parse(Console.ReadLine());
        switch (x)
        {
            case 1:
                Console.WriteLine("one");
                break;
            case 2:
                Console.WriteLine("two");
                break;
            default:
                Console.WriteLine("many");
                break;
        }

        try
        {
            Console.WriteLine(Divide(x, 2));
        }
        catch (DivideByZeroException e)
        {
            Console.WriteLine(e.Message);
        }
        finally
        {
            Console.WriteLine("done");
        }
    }

    static int Divide(int a, int b)
    {
        if (b == 0)
        {
            return 0;
        }
        return a / b;
    }
}
